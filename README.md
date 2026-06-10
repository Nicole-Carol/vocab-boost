# 📖 Vocab-boost

Vocab-boost é um leitor de PDFs em inglês com ferramentas integradas para aprendizado de idiomas. Ele extrai o texto de cada página, organiza os parágrafos de forma inteligente e permite traduzir palavras com um clique. Inclui ainda sistema de flashcards com revisão espaçada, prática de escrita, metas diárias e dashboards de progresso — tudo num único ambiente web.

![HTML5](https://img.shields.io/badge/HTML5-E34F26?style=flat&logo=html5&logoColor=white)
![CSS3](https://img.shields.io/badge/CSS3-1572B6?style=flat&logo=css3&logoColor=white)
![JavaScript](https://img.shields.io/badge/JavaScript-F7DF1E?style=flat&logo=javascript&logoColor=black)
![PDF.js](https://img.shields.io/badge/PDF.js-F40F02?style=flat&logo=adobe-acrobat-reader&logoColor=white)
![Chart.js](https://img.shields.io/badge/Chart.js-FF6384?style=flat&logo=chartdotjs&logoColor=white)
![PWA](https://img.shields.io/badge/PWA-Ready-5A0FC8?style=flat&logo=pwa&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat&logo=fastapi&logoColor=white)
![MySQL](https://img.shields.io/badge/MySQL-4479A1?style=flat&logo=mysql&logoColor=white)

## 🎯 Funcionalidades principais

- **Leitor de PDF** com extração de texto parágrafo a parágrafo
- **Tradução e análise de palavras** ao clicar sobre elas (integração com IA)
- **Salvamento de frases** direto do PDF para decks personalizados
- **Sistema de flashcards** com cartões 3D e revisão espaçada (Esqueci / Difícil / Fácil)
- **Modos de revisão rápida**: Quiz e Ditado com reconhecimento de voz
- **Prática de escrita**: comparar frases com originais, detecção de erros gramaticais
- **Metas diárias** com barra de progresso e confetes ao atingir a meta
- **Dashboards**: gráficos de revisões, acertos por deck e evolução de pontos
- **PWA**: funciona offline e pode ser instalado como aplicativo

## 🧠 Origem e desenvolvimento

Este projeto nasceu de uma necessidade pessoal: ler livros em inglês sem ter que parar constantemente para procurar palavras.  
**Toda a concepção, funcionalidades e fluxos foram idealizados por mim.**

Para acelerar a implementação, utilizei **modelos de inteligência artificial generativa** como assistente na escrita do código HTML, CSS e JavaScript.  
A IA gerou trechos de código com base nas minhas orientações, e eu assumi o papel de **revisor, testador e arquiteto**:

- Defini quais tecnologias usar (PDF.js, Chart.js, Free Dictionary API, Gemini)
- Estruturei a interface e a experiência do usuário
- Corrigi bugs (como imagens enrugadas, parágrafos desorganizados, cores e tamanhos de fonte)
- Adaptei funcionalidades para atender exatamente ao que eu precisava
- Validei cada parte do sistema até ficar estável

**O projeto é fruto de um processo moderno de desenvolvimento, onde a IA foi uma ferramenta — como um editor de código ou uma biblioteca — e não a criadora.**

## 📚 Tecnologias utilizadas

| Tecnologia | Uso |
|------------|-----|
| **PDF.js** | Renderização e extração de texto dos PDFs |
| **Chart.js** | Gráficos interativos (progresso, acertos, pontos) |
| **Free Dictionary API** | Áudio e definições de palavras em inglês |
| **Google Generative AI (Gemini)** | Traduções e análises de palavras (via backend) |
| **Canvas Confetti** | Efeito de confetes ao atingir a meta diária |
| **Service Worker** | Cache offline e comportamento de PWA |
| **Font Awesome** | Ícones da interface |
| **FastAPI (Python)** | Backend da aplicação |
| **MySQL** | Banco de dados relacional |
| **SQLAlchemy** | ORM para acesso ao banco |

## 🚀 Como rodar o projeto completo

### 📋 Pré‑requisitos
- **Python 3.8+** e pip
- **MySQL** (local ou remoto)
- Navegador moderno (Chrome, Firefox, Edge)

### 1️⃣ Clone o repositório
```bash
git clone https://github.com/seu-usuario/vocab-boost.git
cd vocab-boost

2️⃣ Backend (FastAPI + MySQL)
🔧 Instalação das dependências Python
Crie um ambiente virtual (recomendado):

bash
python -m venv venv
source venv/bin/activate   # no Windows: venv\Scripts\activate
Instale os pacotes:

bash
pip install -r requirements.txt
🗄️ Configuração do banco de dados MySQL
Crie um banco de dados no MySQL (ex: vocab_boost).
Acesse o terminal do MySQL e execute:

sql
CREATE DATABASE vocab_boost CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
Configure as credenciais de acesso no arquivo .env (crie um arquivo .env na raiz do projeto):

text
DATABASE_URL=mysql+mysqlconnector://USUARIO:SENHA@localhost/vocab_boost
GEMINI_API_KEY=sua-chave-da-api-gemini
Substitua USUARIO, SENHA e localhost pelos seus dados.
Se o MySQL estiver em outra porta ou host, ajuste a string de conexão.

As tabelas serão criadas automaticamente na primeira execução do servidor (graças ao SQLAlchemy).

🗝️ Chave da API Gemini
Acesse Google AI Studio e crie uma chave gratuita.

Cole a chave no arquivo .env, como mostrado acima.

▶️ Executando o servidor
No diretório raiz, com o ambiente virtual ativo:

bash
uvicorn app:app --reload
O servidor estará rodando em http://127.0.0.1:8000.

Para permitir acesso de outros dispositivos na rede (ex: celular):

bash
uvicorn app:app --host 0.0.0.0 --port 8000 --reload
Anote o IP do seu computador (ex: 192.168.0.10) para acessar o frontend pelo celular.

3️⃣ Frontend (HTML/CSS/JS)
O frontend é totalmente estático e pode ser servido pelo próprio FastAPI (se você adicionou StaticFiles no backend) ou por qualquer servidor HTTP simples.

Se o backend já serve os arquivos estáticos, acesse diretamente:

text
http://localhost:8000/unificado.html
Caso contrário, use um servidor estático como o serve (Node.js) ou até o Python:

bash
# opção com Python (básico)
python -m http.server 3000
# acesse http://localhost:3000/unificado.html
Importante: o frontend precisa apontar para o backend. No arquivo unificado.html, verifique se a constante API_BASE ou as chamadas fetch estão configuradas para o endereço correto (ex: http://localhost:8000). Ajuste conforme necessário.

📱 Acessando pelo celular (rede local)
Inicie o backend com --host 0.0.0.0 --port 8000.

Descubra o IP do seu computador na rede (use ipconfig no Windows ou hostname -I no Linux/Mac).

No celular, acesse: http://192.168.x.x:8000/unificado.html (substitua pelo IP real).

📂 Estrutura do projeto
text
.
├── app.py                 # Código principal do FastAPI
├── models.py              # Modelos do banco de dados (SQLAlchemy)
├── requirements.txt       # Dependências Python
├── .env                   # Variáveis de ambiente (ignorado pelo Git)
├── unificado.html         # Front‑end completo
├── style.css              # Estilos carregados externamente
├── sw.js                  # Service Worker (PWA)
├── manifest.json          # Manifesto PWA
├── logo.png               # Logotipo
└── README.md
✅ Testando a API
Com o servidor rodando, acesse a documentação interativa (Swagger):

text
http://localhost:8000/docs
Lá você pode testar todos os endpoints (/decks, /revisar, /analisar, etc.) diretamente pelo navegador.

📸 Screenshots
(Adicione aqui capturas de tela do projeto funcionando)

🤝 Contribuições
Contribuições são bem‑vindas! Sinta‑se à vontade para abrir issues ou pull requests.

📝 Licença
Este projeto está sob a licença MIT. Veja o arquivo LICENSE para mais detalhes.
 Feito com 💙 e muitas horas de teste por Nicole caroline. 


Substitua os placeholders pelo seu usuário do GitHub, nome e detalhes corretos. Depois é só colar no final do seu arquivo README.md. Se precisar de mais algum ajuste, é só pedir!


