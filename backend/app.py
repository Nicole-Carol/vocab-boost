import os
import io
import re
import json
import logging
import asyncio
from datetime import datetime
from typing import Optional, Union
from concurrent.futures import ThreadPoolExecutor
import requests
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse, StreamingResponse
from pydantic import BaseModel
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.units import cm
from englishidioms import find_idioms
from services.database import PalavraRepository
from services.gemini_service import analisar_texto, traduzir_apenas
from models import Palavra
import PyPDF2

# ---------- LOGGER ----------
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

# ---------- APP ----------
app = FastAPI(max_request_size=10_485_760)

# ========================================================
# MIDDLEWARE DE SEGURANÇA (DESATIVADO TEMPORARIAMENTE)
# ========================================================
# @app.middleware("http")
# async def add_security_headers(request, call_next):
#     response = await call_next(request)
#     response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
#     response.headers["X-Content-Type-Options"] = "nosniff"
#     response.headers["X-Frame-Options"] = "DENY"
#     response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com https://cdn.jsdelivr.net; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; connect-src 'self' https://api.dictionaryapi.dev https://api.datamuse.com;"
#     return response

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

repo = PalavraRepository()

# ---------- GARANTIR DECK "MANUAL" ----------
try:
    decks_existentes = repo.listar_decks()
    if not any(d['nome'] == 'Manual' for d in decks_existentes):
        repo.criar_deck('Manual')
        logger.info("Deck 'Manual' criado automaticamente")
except Exception as e:
    logger.error(f"Erro ao verificar/criar deck Manual: {e}")

# ---------- MODELOS EXISTENTES ----------
class TextoRequest(BaseModel):
    termo: str
    frase: str
    deck_id: Optional[int] = None

class RevisaoRequest(BaseModel):
    termo: str
    qualidade: int

class AtualizarRequest(BaseModel):
    termo: str
    traducao: str = ""
    contexto: str = ""

class DeckRequest(BaseModel):
    nome: str

class AssociarDeckRequest(BaseModel):
    termo: str
    deck_id: Optional[int] = None

class NotasRequest(BaseModel):
    termo: str
    notas: str = ""

# ---------- NOVOS MODELOS (frases e regras) ----------
class FraseSalvaRequest(BaseModel):
    frase: str
    deck_id: Optional[int] = None
    palavra_origem: Optional[str] = None

class RegraGramaticalRequest(BaseModel):
    padrao: str
    sugestao: str
    explicacao: Optional[str] = None

class FraseRevisaoRequest(BaseModel):
    frase_id: int
    deck_id: Optional[int] = None

# ---------- FUNÇÕES AUXILIARES ----------
def verificar_internet():
    try:
        requests.get("https://google.com", timeout=3)
        return True
    except requests.exceptions.RequestException:
        return False

def extrair_traducao_limpa(texto):
    if not texto:
        return ""
    match = re.search(r'📝 TRADUÇÃO:\s*(.+?)(\n|$)', texto)
    if match:
        return match.group(1).strip()
    match = re.search(r'tradução:\s*(.+?)(\n|$)', texto, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    linhas = [l.strip() for l in texto.split('\n') if l.strip() and not re.match(r'^[📖📝🗣️📄⚠️═─]', l.strip())]
    if linhas:
        return linhas[0]
    return texto.strip()

def consultar_dicionario(termo: str):
    try:
        response = requests.get(f"https://api.dictionaryapi.dev/api/v2/entries/en/{termo}", timeout=5)
        if response.status_code == 200:
            dados = response.json()
            if dados and len(dados) > 0:
                significado = dados[0]['meanings'][0]['definitions'][0]
                return {
                    'definicao': significado.get('definition', ''),
                    'exemplo': significado.get('example', ''),
                    'audio_url': dados[0]['phonetics'][0]['audio'] if dados[0].get('phonetics') and dados[0]['phonetics'][0].get('audio') else None
                }
    except Exception as e:
        logger.warning(f"Erro ao consultar dicionário: {e}")
    return {'definicao': '', 'exemplo': '', 'audio_url': None}

def consultar_idioms(termo: str, frase: str):
    if not frase:
        return []
    try:
        idioms = find_idioms(frase, limit=5)
        return [{'phrase': i['phrase'], 'definition': i['definition']} 
                for i in idioms if termo.lower() in i['phrase'].lower()]
    except Exception as e:
        logger.warning(f"Erro ao consultar idioms: {e}")
        return []

# ========================================================
# ROTAS EXISTENTES (não alteradas)
# ========================================================

@app.get("/sinonimos/{palavra}")
def obter_sinonimos(palavra: str):
    try:
        resp = requests.get(f"https://api.datamuse.com/words?rel_syn={palavra}&max=10", timeout=5)
        if resp.status_code == 200:
            dados = resp.json()
            sinonimos = [item['word'] for item in dados]
            return {"sinonimos": sinonimos}
    except Exception as e:
        logger.warning(f"Erro ao obter sinónimos: {e}")
    return {"sinonimos": []}

@app.get("/palavra/{termo}")
def obter_palavra(termo: str):
    palavra = repo.buscar(termo)
    if not palavra:
        raise HTTPException(404, "Palavra não encontrada")
    return palavra

@app.post("/extrair-texto-pdf")
async def extrair_texto_pdf(file: UploadFile = File(...)):
    try:
        contents = await file.read()
        pdf_reader = PyPDF2.PdfReader(io.BytesIO(contents))
        texto_completo = []
        for page in pdf_reader.pages:
            texto = page.extract_text()
            if texto:
                texto_completo.append(texto)
        return {"texto": "\n".join(texto_completo)}
    except Exception as e:
        logger.error(f"Erro ao extrair texto do PDF: {e}")
        raise HTTPException(500, "Erro ao processar o PDF")

@app.post("/analisar")
async def analisar(request: TextoRequest):
    termo = request.termo.strip().lower()
    logger.info(f"Analisando termo: {termo}")

    resultado_db = repo.buscar(termo)
    if resultado_db:
        deck_id = resultado_db.get('deck_id')
        deck_nome = None
        if deck_id:
            deck_info = repo.obter_deck_por_id(deck_id)
            deck_nome = deck_info['nome'] if deck_info else None
        return {
            "origem": "mysql",
            "dados": resultado_db,
            "ja_existe": True,
            "deck_nome": deck_nome
        }

    if not verificar_internet():
        return {"erro": "Sem internet e termo não catalogado."}

    loop = asyncio.get_running_loop()
    with ThreadPoolExecutor() as executor:
        ia_future = loop.run_in_executor(executor, analisar_texto, request.termo, request.frase)
        dict_future = loop.run_in_executor(executor, consultar_dicionario, termo)
        idioms_future = loop.run_in_executor(executor, consultar_idioms, termo, request.frase)
        
        resposta_ia, dados_dicionario, expressoes = await asyncio.gather(
            ia_future, dict_future, idioms_future
        )

    palavra = Palavra(
        termo=termo,
        traducao=resposta_ia,
        contexto=request.frase,
        gramatica=""
    )
    if request.deck_id:
        palavra.deck_id = request.deck_id
    repo.salvar(palavra)

    return {
        "origem": "gemini",
        "dados": {
            "termo": termo,
            "traducao": resposta_ia,
            "contexto": request.frase,
            "gramatica": ""
        },
        "definicao": dados_dicionario.get('definicao', ''),
        "exemplo": dados_dicionario.get('exemplo', ''),
        "audio_url": dados_dicionario.get('audio_url'),
        "expressoes": expressoes
    }

@app.post("/adicionar-palavra")
def adicionar_palavra(request: TextoRequest):
    termo = request.termo.strip().lower()
    logger.info(f"Adicionando palavra: {termo}")

    existente = repo.buscar(termo)
    if existente:
        return {
            "existe": True,
            "mensagem": f"A palavra '{termo}' já está salva!",
            "dados": existente
        }

    palavra = Palavra(termo=termo, contexto=request.frase)
    resposta_ia = analisar_texto(request.termo, request.frase)
    palavra.traducao = resposta_ia
    palavra.gramatica = "Manual"

    if request.deck_id:
        palavra.deck_id = request.deck_id

    repo.salvar(palavra)

    return {
        "existe": False,
        "mensagem": "Palavra salva com sucesso!",
        "dados": palavra.to_dict()
    }

@app.put("/atualizar-palavra")
def atualizar_palavra(request: AtualizarRequest):
    termo = request.termo.strip().lower()
    existente = repo.buscar(termo)
    if not existente:
        return {"erro": "Palavra não encontrada"}
    repo.atualizar(termo, nova_traducao=request.traducao, novo_contexto=request.contexto)
    return {"mensagem": "Palavra atualizada com sucesso!"}

@app.put("/atualizar-notas")
def atualizar_notas(request: NotasRequest):
    termo = request.termo.strip().lower()
    notas = request.notas.strip()
    logger.info(f"Atualizando notas para: {termo}")
    repo.atualizar_notas(termo, notas)
    return {"mensagem": "Notas salvas com sucesso!"}

@app.get("/palavras")
def listar_palavras(deck_id: Optional[int] = None, sem_deck: Optional[bool] = False):
    if sem_deck:
        palavras = repo.listar_sem_deck()
    elif deck_id is not None:
        palavras = repo.listar_por_deck(deck_id)
    else:
        palavras = repo.listar_todas()
    return {"palavras": palavras}

@app.get("/adicionar", response_class=HTMLResponse)
def pagina_adicionar():
    return """
    <!DOCTYPE html>
    <html>
    <head><meta charset="UTF-8"><title>Adicionar</title></head>
    <body>
        <h2>Adicionar Palavra</h2>
        <input type="text" id="termo" placeholder="Termo">
        <textarea id="frase" placeholder="Frase"></textarea>
        <button onclick="adicionar()">Salvar</button>
        <div id="resultado"></div>
        <script>
            async function adicionar() {
                const termo = document.getElementById('termo').value;
                const frase = document.getElementById('frase').value;
                const res = await fetch('/adicionar-palavra', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({termo, frase})
                });
                const data = await res.json();
                document.getElementById('resultado').innerHTML = JSON.stringify(data);
            }
        </script>
    </body>
    </html>
    """

@app.get("/ler-pdf", response_class=HTMLResponse)
def pagina_pdf():
    with open("leitor_pdf.html", "r", encoding="utf-8") as f:
        return f.read()

@app.get("/", response_class=HTMLResponse)
def unificado():
    with open("unificado.html", "r", encoding="utf-8") as f:
        return f.read()

@app.get("/app.js")
def serve_app_js():
    return FileResponse("app.js", media_type="application/javascript")

@app.get("/sw.js")
def serve_sw_js():
    return FileResponse("sw.js", media_type="application/javascript")

@app.get("/manifest.json")
def serve_manifest():
    return FileResponse("manifest.json", media_type="application/json")

@app.get("/style.css")
def serve_css():
    return FileResponse("style.css", media_type="text/css")

@app.get("/logo.png")
def serve_logo():
    return FileResponse("logo.png", media_type="image/png")

@app.post("/traduzir-frase")
def traduzir_frase(frase: str = Form(...)):
    traducao = traduzir_apenas(frase)
    return {"traducao": traducao}

@app.get("/revisar")
def listar_revisoes(deck_id: Optional[int] = None):
    palavras = repo.buscar_pendentes(deck_id)
    for p in palavras:
        if isinstance(p.get('ultima_revisao'), datetime):
            p['ultima_revisao'] = p['ultima_revisao'].isoformat()
    return {"palavras": palavras, "total": len(palavras)}

@app.post("/revisar")
def registrar_revisao(request: RevisaoRequest):
    if request.qualidade < 0 or request.qualidade > 5:
        return {"erro": "Qualidade deve ser entre 0 e 5"}
    resultado = repo.atualizar_revisao(request.termo, request.qualidade)
    if resultado is None:
        return {"erro": "Termo não encontrado"}
    return resultado

@app.get("/decks")
def listar_decks():
    return {"decks": repo.listar_decks()}

@app.post("/decks")
def criar_deck(request: DeckRequest):
    deck_id = repo.criar_deck(request.nome)
    return {"id": deck_id, "nome": request.nome}

@app.put("/decks/{deck_id}")
def editar_deck(deck_id: int, request: DeckRequest):
    repo.editar_deck(deck_id, request.nome)
    return {"mensagem": "Deck atualizado"}

@app.delete("/decks/{deck_id}")
def excluir_deck(deck_id: int):
    repo.excluir_deck(deck_id)
    return {"mensagem": "Deck excluído"}

@app.put("/associar-deck")
def associar_deck(request: AssociarDeckRequest):
    repo.associar_deck(request.termo, request.deck_id)
    return {"mensagem": "Palavra associada ao deck"}

@app.get("/exportar-pdf")
def exportar_pdf(deck_id: Optional[int] = None):
    if deck_id:
        palavras = repo.listar_por_deck(deck_id)
    else:
        palavras = repo.listar_todas()
    
    pdf_buffer = io.BytesIO()
    doc = SimpleDocTemplate(pdf_buffer, pagesize=A4,
                            leftMargin=1.5*cm, rightMargin=1.5*cm,
                            topMargin=2*cm, bottomMargin=2*cm)
    
    styles = getSampleStyleSheet()
    title_style = styles['Title']
    normal_style = ParagraphStyle('Normal', fontSize=10, leading=14)
    
    data = [[Paragraph('<b>Termo</b>', normal_style),
             Paragraph('<b>Tradução</b>', normal_style),
             Paragraph('<b>Contexto</b>', normal_style)]]
    
    for p in palavras:
        traducao_limpa = extrair_traducao_limpa(p.get('traducao', ''))
        contexto = p.get('contexto', '') or ''
        termo_cap = p['termo'].capitalize()
        traducao_cap = traducao_limpa.capitalize()
        data.append([Paragraph(termo_cap, normal_style),
                     Paragraph(traducao_cap, normal_style),
                     Paragraph(contexto, normal_style)])
    
    col_widths = [4*cm, 5*cm, 9*cm]
    table = Table(data, colWidths=col_widths, repeatRows=1)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4a6a8a')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f5f5f5')])
    ]))
    
    title = Paragraph("Palavras Salvas", title_style)
    elements = [title, table]
    doc.build(elements)
    pdf_buffer.seek(0)
    
    return StreamingResponse(pdf_buffer, media_type="application/pdf",
                             headers={"Content-Disposition": "attachment; filename=palavras.pdf"})

@app.get("/dashboard")
def dashboard(dias: int = 30):
    return repo.obter_dashboard(dias)

@app.get("/progresso")
def progresso():
    return repo.obter_progresso()

@app.get("/estatisticas")
def obter_estatisticas():
    return repo.obter_estatisticas()

@app.get("/estatisticas-por-deck")
def estatisticas_por_deck():
    try:
        return repo.obter_estatisticas_por_deck()
    except Exception as e:
        logger.error(f"Erro ao obter estatísticas por deck: {e}")
        return {"erro": str(e)}

@app.get("/evolucao-pontos")
def evolucao_pontos(dias: int = 30):
    try:
        return repo.obter_evolucao_pontos(dias)
    except Exception as e:
        logger.error(f"Erro ao obter evolução de pontos: {e}")
        return {"erro": str(e)}

# ========================================================
# NOVAS ROTAS (salvar frases, paginação, revisão de frases)
# ========================================================

@app.post("/salvar-frase")
async def salvar_frase(request: FraseSalvaRequest):
    """
    Guarda uma frase (extraída de um PDF) associada a um deck (opcional).
    Verifica duplicata em qualquer deck (não apenas no mesmo) e retorna o nome do deck onde já existe.
    """
    try:
        # Verificar se a frase já existe em algum deck (globalmente)
        existe_em = repo.verificar_frase_em_qualquer_deck(request.frase)
        if existe_em:
            deck_nome = existe_em.get('deck_nome') or "Sem deck"
            raise HTTPException(
                status_code=409,
                detail=f"Frase já existe no deck '{deck_nome}'. Não é possível salvar duplicatas."
            )
        
        frase_id = repo.salvar_frase(
            frase=request.frase,
            deck_id=request.deck_id,
            palavra_origem=request.palavra_origem
        )
        return {"message": "Frase salva com sucesso!", "id": frase_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao salvar frase: {e}")
        raise HTTPException(500, f"Erro ao salvar frase: {str(e)}")

@app.get("/frases-por-deck/{deck_param}")
def listar_frases_por_deck(deck_param: str):
    """
    Retorna frases de acordo com o parâmetro:
    - 'all' : todas as frases (qualquer deck)
    - 'none': frases sem deck (deck_id IS NULL)
    - número: frases do deck com esse ID
    """
    try:
        if deck_param == 'all':
            frases = repo.listar_todas_frases()
        elif deck_param == 'none':
            frases = repo.listar_frases_sem_deck()
        else:
            deck_id = int(deck_param)
            frases = repo.listar_frases_por_deck(deck_id)
        return frases
    except Exception as e:
        logger.error(f"Erro ao listar frases: {e}")
        raise HTTPException(500, f"Erro ao listar frases: {str(e)}")

@app.get("/frases-por-deck/{deck_param}/paginado")
def listar_frases_paginado(
    deck_param: str,
    pagina: int = 1,
    por_pagina: int = 10,
    busca: str = ""
):
    """Retorna frases paginadas e total de registos, com busca opcional."""
    try:
        frases, total = repo.obter_frases_por_deck_paginado(deck_param, pagina, por_pagina, busca)
        return {"frases": frases, "total": total}
    except Exception as e:
        logger.error(f"Erro ao listar frases paginadas: {e}")
        raise HTTPException(500, f"Erro ao listar frases: {str(e)}")

@app.post("/frase-revisao")
def marcar_revisao(request: FraseRevisaoRequest):
    """Marca uma frase para revisão (quando o utilizador erra ao escrever)."""
    try:
        repo.adicionar_frase_revisao(request.frase_id, request.deck_id)
        return {"mensagem": "Frase marcada para revisão"}
    except Exception as e:
        logger.error(f"Erro ao marcar revisão: {e}")
        raise HTTPException(500, f"Erro ao marcar revisão: {str(e)}")

@app.get("/frases-revisao/{deck_param}")
def obter_frases_revisao(deck_param: str, limite: int = 10):
    """Retorna frases pendentes de revisão de um deck."""
    try:
        frases = repo.obter_frases_revisao_por_deck(deck_param, limite)
        return {"frases": frases}
    except Exception as e:
        logger.error(f"Erro ao obter frases de revisão: {e}")
        raise HTTPException(500, f"Erro ao obter frases de revisão: {str(e)}")

@app.post("/frase-revisada")
def marcar_revisada(request: dict):
    """Marca uma frase como já revista (após o utilizador acertar)."""
    try:
        frase_id = request.get("frase_id")
        if not frase_id:
            raise HTTPException(400, "Frase ID é obrigatório")
        repo.marcar_frase_revisada(frase_id)
        return {"mensagem": "Frase marcada como revista"}
    except Exception as e:
        logger.error(f"Erro ao marcar frase revista: {e}")
        raise HTTPException(500, f"Erro ao marcar frase revista: {str(e)}")

@app.post("/adicionar-regra")
async def adicionar_regra(request: RegraGramaticalRequest):
    """Adiciona uma nova regra gramatical (padrão, sugestão, explicação)."""
    try:
        regra_id = repo.adicionar_regra(
            padrao=request.padrao,
            sugestao=request.sugestao,
            explicacao=request.explicacao
        )
        return {"message": "Regra adicionada com sucesso!", "id": regra_id}
    except Exception as e:
        logger.error(f"Erro ao adicionar regra: {e}")
        raise HTTPException(500, f"Erro ao adicionar regra: {str(e)}")

@app.get("/regras-gramaticais")
def listar_regras():
    """Lista todas as regras gramaticais (ativas e inativas)."""
    try:
        regras = repo.listar_regras()
        return regras
    except Exception as e:
        logger.error(f"Erro ao listar regras: {e}")
        raise HTTPException(500, f"Erro ao listar regras: {str(e)}")

@app.post("/verificar-regras")
async def verificar_regras(request: dict):
    """Recebe uma frase e retorna as regras cujo padrão aparece na frase."""
    try:
        frase = request.get("frase", "").lower()
        regras = repo.listar_regras_ativas()
        erros = []
        for regra in regras:
            padrao = regra["padrao"].lower()
            if padrao in frase:
                erros.append({
                    "padrao": regra["padrao"],
                    "sugestao": regra["sugestao"],
                    "explicacao": regra.get("explicacao", "")
                })
        return {"erros": erros}
    except Exception as e:
        logger.error(f"Erro ao verificar regras: {e}")
        raise HTTPException(500, f"Erro ao verificar regras: {str(e)}")

# ---------- INICIALIZAÇÃO DO SERVIDOR ----------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)