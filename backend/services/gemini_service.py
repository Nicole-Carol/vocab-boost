import google.genai as genai
from config import GEMINI_API_KEY
from deep_translator import GoogleTranslator
import requests
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

# Inicializa o cliente Gemini com a chave do config
client = genai.Client(api_key=GEMINI_API_KEY)

def analisar_com_gemini(termo, frase):
    """
    Envia o termo e a frase para o modelo Gemini e retorna a análise completa.

    Args:
        termo (str): palavra ou expressão em inglês a ser analisada.
        frase (str): frase de contexto onde o termo aparece.

    Returns:
        str: resposta textual do Gemini com tradução, explicação gramatical etc.

    Raises:
        genai.errors.ClientError: se ocorrer erro na API (cota, rede etc.).
    """
    prompt = f"""
    Você é um professor especialista em inglês.

    Analise o termo abaixo dentro da frase.

    Termo:
    {termo}

    Frase:
    {frase}

    Explique em português:

    - tradução
    - significado no contexto
    - explicação gramatical
    - phrasal verb
    - gíria
    - tempo verbal
    """
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=prompt
    )
    return response.text


def analisar_com_tradutor(termo, frase):
    """
    Fallback de análise usando tradutor e dicionário online.
    Não inclui pronúncia e retorna tipos gramaticais traduzidos.

    Args:
        termo (str): palavra ou expressão em inglês.
        frase (str): frase de contexto.

    Returns:
        str: análise formatada com tradução, definição, exemplos etc.
    """
    # 1. Tradução
    try:
        tradutor = GoogleTranslator(source='en', target='pt')
        traducao = tradutor.translate(termo)
    except requests.exceptions.RequestException as e:
        logger.error(f"Erro de rede ao traduzir '{termo}': {e}")
        traducao = "Tradução não disponível"

    # 2. Tipo gramatical (com dicionário em português)
    tipo_gramatical = ""
    try:
        if len(termo.split()) > 1:
            tipo_gramatical = "phrasal verb"
        else:
            url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{termo}"
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                dados = response.json()
                if dados and "meanings" in dados[0]:
                    tipo_gramatical = dados[0]['meanings'][0]['partOfSpeech']
    except requests.exceptions.RequestException as e:
        logger.warning(f"Erro ao obter tipo gramatical para '{termo}': {e}")

    # 3. Definição, exemplos e sinônimos (mantidos, mas sem pronúncia)
    definicao = ""
    exemplos = []
    sinonimos = []
    try:
        palavra_busca = termo.split()[0] if " " in termo else termo
        url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{palavra_busca}"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            dados = response.json()
            if dados and len(dados) > 0:
                palavra_dados = dados[0]
                if "meanings" in palavra_dados:
                    for meaning in palavra_dados["meanings"]:
                        if "definitions" in meaning:
                            for defs in meaning["definitions"][:3]:
                                if not definicao and "definition" in defs:
                                    definicao = defs["definition"]
                                if "example" in defs and len(exemplos) < 2:
                                    exemplos.append(defs["example"])
                        if "synonyms" in meaning and len(sinonimos) < 5:
                            sinonimos.extend(meaning["synonyms"][:5])
    except requests.exceptions.RequestException as e:
        logger.warning(f"Erro ao buscar definições para '{palavra_busca}': {e}")

    # 4. Traduzir frase completa
    frase_traduzida = ""
    try:
        frase_traduzida = tradutor.translate(frase)
    except requests.exceptions.RequestException as e:
        logger.error(f"Erro ao traduzir a frase: {e}")

    # 5. Montar resposta (sem pronúncia, tipo sempre em português)
    resposta = "═" * 50 + "\n"
    resposta += f"📖 TERMO: {termo}\n"
    resposta += "═" * 50 + "\n\n"

    resposta += f"📝 TRADUÇÃO: {traducao}\n\n"

    if tipo_gramatical:
        emoji_tipo = {
            "noun": "📚 Substantivo",
            "verb": "⚡ Verbo",
            "adjective": "🎨 Adjetivo",
            "adverb": "💨 Advérbio",
            "phrasal verb": "🔗 Phrasal Verb",
            "preposition": "📍 Preposição",
            "conjunction": "🔗 Conjunção",
            "interjection": "😮 Interjeição",
            "pronoun": "👤 Pronome"
        }
        tipo_formatado = emoji_tipo.get(tipo_gramatical.lower(), f"📚 {tipo_gramatical}")
        resposta += f"{tipo_formatado}\n\n"

    if definicao:
        resposta += f"📖 DEFINIÇÃO (inglês):\n   {definicao}\n\n"

    if exemplos:
        resposta += "📋 EXEMPLOS:\n"
        for ex in exemplos:
            resposta += f"   • {ex}\n"
        resposta += "\n"

    if sinonimos:
        resposta += f"🔄 SINÔNIMOS: {', '.join(sinonimos[:5])}\n\n"

    resposta += "─" * 50 + "\n"
    resposta += f"📄 FRASE ORIGINAL:\n   \"{frase}\"\n\n"
    if frase_traduzida:
        resposta += f"🔄 FRASE TRADUZIDA:\n   \"{frase_traduzida}\"\n\n"

    resposta += "─" * 50 + "\n"
    resposta += "⚠️ Análise por dicionário (IA indisponível)\n"
    resposta += "═" * 50

    return resposta


def analisar_texto(termo, frase):
    """
    Tenta análise com IA (Gemini); se falhar, usa tradutor.

    Args:
        termo (str): palavra ou expressão em inglês.
        frase (str): frase de contexto.

    Returns:
        str: análise completa ou fallback.
    """
    try:
        logger.info(f"🤖 Iniciando análise com IA para: {termo}")
        resultado = analisar_com_gemini(termo, frase)
        logger.info("✅ Análise com IA concluída")
        return resultado
    except genai.errors.ClientError as e:
        logger.warning(f"⚠️ Erro na API Gemini: {e}")
        if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
            logger.warning("⏰ Cota da IA excedida")
        return analisar_com_tradutor(termo, frase)
    except Exception as e:
        logger.error(f"Erro inesperado na análise IA: {e}")
        return analisar_com_tradutor(termo, frase)


def traduzir_apenas(texto):
    """
    Traduz um texto simples (palavra ou frase) usando GoogleTranslator.

    Args:
        texto (str): texto em inglês.

    Returns:
        str: tradução em português ou mensagem de erro.
    """
    try:
        tradutor = GoogleTranslator(source='en', target='pt')
        return tradutor.translate(texto)
    except requests.exceptions.RequestException as e:
        logger.error(f"Erro na tradução simples de '{texto}': {e}")
        return "Tradução indisponível"