from deep_translator import GoogleTranslator
import requests

def traduzir_e_analisar(termo, frase):
    """
    Traduz e analisa termo/frase sem usar IA paga
    """
    
    resultado = {
        "termo": termo,
        "traducao": "",
        "pronuncia": "",
        "tipo": "",
        "definicao": "",
        "exemplos": []
    }
    
    try:
        # 1. TRADUÇÃO (Google Translate grátis)
        tradutor = GoogleTranslator(source='en', target='pt')
        resultado["traducao"] = tradutor.translate(termo)
        
        # 2. PRONÚNCIA (API gratuita)
        try:
            url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{termo}"
            response = requests.get(url)
            if response.status_code == 200:
                dados = response.json()
                if dados and "phonetics" in dados[0]:
                    for phon in dados[0]["phonetics"]:
                        if "text" in phon:
                            resultado["pronuncia"] = phon["text"]
                            break
                
                # 3. TIPO (substantivo, verbo, etc)
                if dados and "meanings" in dados[0]:
                    resultado["tipo"] = dados[0]["meanings"][0]["partOfSpeech"]
                    
                    # 4. DEFINIÇÃO em inglês
                    if dados[0]["meanings"][0]["definitions"]:
                        resultado["definicao"] = dados[0]["meanings"][0]["definitions"][0]["definition"]
                        
                        # 5. EXEMPLOS
                        for defs in dados[0]["meanings"][0]["definitions"][:3]:
                            if "example" in defs:
                                resultado["exemplos"].append(defs["example"])
        except:
            pass
        
        # 6. VERIFICAR SE É PHRASAL VERB
        if " " in termo and len(termo.split()) > 1:
            resultado["tipo"] = "Phrasal Verb"
        
    except Exception as e:
        resultado["erro"] = str(e)
    
    return resultado

def analisar_texto(termo, frase):
    """
    Função compatível com seu sistema atual
    """
    resultado = traduzir_e_analisar(termo, frase)
    
    # Formatar resposta bonita
    resposta = f"""
📖 ANÁLISE DO TERMO: {termo}

📝 TRADUÇÃO: {resultado.get('traducao', 'Não disponível')}

🗣️ PRONÚNCIA: {resultado.get('pronuncia', 'Não disponível')}

📚 TIPO: {resultado.get('tipo', 'Não identificado')}

📖 DEFINIÇÃO (inglês): {resultado.get('definicao', 'Não disponível')}
"""
    
    if resultado.get('exemplos'):
        resposta += "\n📋 EXEMPLOS:\n"
        for ex in resultado['exemplos'][:3]:
            resposta += f"  • {ex}\n"
    
    resposta += f"\n📖 FRASE COMPLETA:\n  {frase}"
    
    return resposta