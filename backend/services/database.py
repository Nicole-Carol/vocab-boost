import mysql.connector
from config import MYSQL_HOST, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DATABASE
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

def get_connection():
    """Retorna uma conexão com o banco de dados MySQL."""
    return mysql.connector.connect(
        host=MYSQL_HOST,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DATABASE
    )

def buscar_termo(termo):
    """Busca um termo na tabela dicionario (função legada)."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    sql = "SELECT * FROM dicionario WHERE termo = %s"
    cursor.execute(sql, (termo.lower(),))
    resultado = cursor.fetchone()
    cursor.close()
    conn.close()
    return resultado

def salvar_termo(termo, traducao, contexto, gramatica):
    """Salva um termo na tabela dicionario (função legada)."""
    conn = get_connection()
    cursor = conn.cursor()
    sql = """
    INSERT INTO dicionario
    (termo, traducao, contexto, gramatica)
    VALUES (%s, %s, %s, %s)
    """
    try:
        cursor.execute(sql, (termo.lower(), traducao, contexto, gramatica))
        conn.commit()
    except mysql.connector.Error as e:
        logger.error(f"Erro ao salvar termo: {e}")
    finally:
        cursor.close()
        conn.close()

class PalavraRepository:
    """Repositório para operações com palavras e decks."""
    
    def __init__(self):
        self.table = "dicionario"
        self.deck_table = "decks"
        self.revisoes_table = "revisoes"
        self.frases_table = "frases_salvas"
        self.regras_table = "regras_gramaticais"
        self.frases_revisao_table = "frases_revisao"
        self._criar_tabela_revisoes()
        self._criar_tabela_frases()
        self._criar_tabela_regras()
        self._criar_tabela_frases_revisao()
        self._garantir_colunas()

    def _criar_tabela_revisoes(self):
        """Cria a tabela de revisões se ela não existir."""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {self.revisoes_table} (
                id INT AUTO_INCREMENT PRIMARY KEY,
                palavra_id INT NOT NULL,
                data_revisao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                qualidade INT NOT NULL CHECK (qualidade BETWEEN 0 AND 5),
                pontos_ganhos INT DEFAULT 0,
                FOREIGN KEY (palavra_id) REFERENCES {self.table}(id) ON DELETE CASCADE
            )
        """)
        conn.commit()
        cursor.close()
        conn.close()
        logger.info("Tabela 'revisoes' verificada/criada com sucesso.")

    def _criar_tabela_frases(self):
        """Cria a tabela de frases salvas se não existir."""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {self.frases_table} (
                id INT AUTO_INCREMENT PRIMARY KEY,
                frase TEXT NOT NULL,
                deck_id INT NULL,
                palavra_origem VARCHAR(255) NULL,
                data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (deck_id) REFERENCES {self.deck_table}(id) ON DELETE SET NULL
            )
        """)
        conn.commit()
        cursor.close()
        conn.close()
        logger.info("Tabela 'frases_salvas' verificada/criada com sucesso.")

    def _criar_tabela_regras(self):
        """Cria a tabela de regras gramaticais se não existir."""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {self.regras_table} (
                id INT AUTO_INCREMENT PRIMARY KEY,
                padrao VARCHAR(255) NOT NULL,
                sugestao VARCHAR(255) NOT NULL,
                explicacao TEXT NULL,
                ativo BOOLEAN DEFAULT TRUE,
                data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        cursor.close()
        conn.close()
        logger.info("Tabela 'regras_gramaticais' verificada/criada com sucesso.")

    def _criar_tabela_frases_revisao(self):
        """Cria a tabela de revisão de frases se não existir."""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {self.frases_revisao_table} (
                id INT AUTO_INCREMENT PRIMARY KEY,
                frase_id INT NOT NULL,
                deck_id INT NULL,
                data_adicao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                revisada BOOLEAN DEFAULT FALSE,
                FOREIGN KEY (frase_id) REFERENCES {self.frases_table}(id) ON DELETE CASCADE,
                FOREIGN KEY (deck_id) REFERENCES {self.deck_table}(id) ON DELETE SET NULL
            )
        """)
        conn.commit()
        cursor.close()
        conn.close()
        logger.info("Tabela 'frases_revisao' verificada/criada com sucesso.")

    def _garantir_colunas(self):
        """Garante que a tabela dicionario possua as colunas necessárias para as novas funcionalidades."""
        conn = get_connection()
        cursor = conn.cursor()
        # Verifica e adiciona coluna 'notas' se não existir
        cursor.execute(f"SHOW COLUMNS FROM {self.table} LIKE 'notas'")
        if not cursor.fetchone():
            cursor.execute(f"ALTER TABLE {self.table} ADD COLUMN notas TEXT")
            logger.info("Coluna 'notas' adicionada à tabela dicionario")
        # Verifica e adiciona coluna 'deck_id' se não existir
        cursor.execute(f"SHOW COLUMNS FROM {self.table} LIKE 'deck_id'")
        if not cursor.fetchone():
            cursor.execute(f"ALTER TABLE {self.table} ADD COLUMN deck_id INT NULL")
            logger.info("Coluna 'deck_id' adicionada à tabela dicionario")
        # Verifica e adiciona colunas de revisão espaçada se não existirem
        for col in ['ultima_revisao', 'intervalo', 'facilidade', 'pontos']:
            cursor.execute(f"SHOW COLUMNS FROM {self.table} LIKE '{col}'")
            if not cursor.fetchone():
                if col == 'ultima_revisao':
                    cursor.execute(f"ALTER TABLE {self.table} ADD COLUMN ultima_revisao DATETIME NULL")
                elif col == 'intervalo':
                    cursor.execute(f"ALTER TABLE {self.table} ADD COLUMN intervalo INT DEFAULT 0")
                elif col == 'facilidade':
                    cursor.execute(f"ALTER TABLE {self.table} ADD COLUMN facilidade FLOAT DEFAULT 2.5")
                elif col == 'pontos':
                    cursor.execute(f"ALTER TABLE {self.table} ADD COLUMN pontos INT DEFAULT 0")
                logger.info(f"Coluna '{col}' adicionada à tabela dicionario")
        conn.commit()
        cursor.close()
        conn.close()

    def salvar(self, palavra):
        """Insere uma palavra no banco de dados e retorna o objeto com id preenchido."""
        conn = get_connection()
        cursor = conn.cursor()
        deck_id = getattr(palavra, 'deck_id', None)
        try:
            if deck_id:
                sql = f"""
                    INSERT INTO {self.table} (termo, traducao, contexto, gramatica, deck_id)
                    VALUES (%s, %s, %s, %s, %s)
                """
                valores = (palavra.termo, palavra.traducao, palavra.contexto, palavra.gramatica, deck_id)
            else:
                sql = f"""
                    INSERT INTO {self.table} (termo, traducao, contexto, gramatica)
                    VALUES (%s, %s, %s, %s)
                """
                valores = (palavra.termo, palavra.traducao, palavra.contexto, palavra.gramatica)
            cursor.execute(sql, valores)
            conn.commit()
            palavra.id = cursor.lastrowid
            logger.info(f"Palavra salva: {palavra.termo}")
        except mysql.connector.Error as e:
            logger.error(f"Erro ao salvar palavra {palavra.termo}: {e}")
        finally:
            cursor.close()
            conn.close()
        return palavra

    def buscar(self, termo):
        """Busca um termo e retorna um dicionário com os dados, ou None."""
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        sql = f"SELECT * FROM {self.table} WHERE termo = %s"
        cursor.execute(sql, (termo.lower().strip(),))
        resultado = cursor.fetchone()
        cursor.close()
        conn.close()
        return resultado

    def listar_todas(self):
        """Retorna todas as palavras cadastradas, ordenadas por termo."""
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        sql = f"SELECT * FROM {self.table} ORDER BY termo"
        cursor.execute(sql)
        resultados = cursor.fetchall()
        cursor.close()
        conn.close()
        return resultados

    def listar_sem_deck(self):
        """Retorna todas as palavras que NÃO estão associadas a nenhum deck (deck_id IS NULL)."""
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        sql = f"SELECT * FROM {self.table} WHERE deck_id IS NULL ORDER BY termo"
        cursor.execute(sql)
        resultados = cursor.fetchall()
        cursor.close()
        conn.close()
        return resultados

    def listar_por_deck(self, deck_id):
        """Retorna todas as palavras de um deck específico."""
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        sql = f"SELECT * FROM {self.table} WHERE deck_id = %s ORDER BY termo"
        cursor.execute(sql, (deck_id,))
        resultados = cursor.fetchall()
        cursor.close()
        conn.close()
        return resultados

    def buscar_pendentes(self, deck_id=None):
        """Retorna palavras que estão atrasadas para revisão, com filtro opcional por deck."""
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        sql = f"""
            SELECT * FROM {self.table}
            WHERE (ultima_revisao IS NULL
                   OR DATE_ADD(ultima_revisao, INTERVAL intervalo DAY) <= NOW())
        """
        params = ()
        if deck_id is not None:
            sql += " AND deck_id = %s"
            params = (deck_id,)
        sql += " ORDER BY ultima_revisao IS NULL DESC, ultima_revisao ASC"
        cursor.execute(sql, params)
        resultados = cursor.fetchall()
        cursor.close()
        conn.close()
        return resultados

    def atualizar_revisao(self, termo, qualidade):
        """
        Aplica o algoritmo SM-2 simplificado e atualiza os campos de revisão.
        Também registra o evento na tabela de revisões e acumula pontos de gamificação.
        """
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute(f"SELECT * FROM {self.table} WHERE termo = %s", (termo.lower(),))
        dados = cursor.fetchone()

        if not dados:
            cursor.close()
            conn.close()
            return None

        palavra_id = dados['id']
        facilidade = float(dados.get('facilidade', 2.5))
        intervalo = int(dados.get('intervalo', 0))
        pontos_atuais = int(dados.get('pontos', 0))

        # Calcular pontos ganhos
        if qualidade >= 3:
            pontos_ganhos = qualidade - 2  # 3 → 1, 4 → 2, 5 → 3
        else:
            pontos_ganhos = 0

        novo_pontos = pontos_atuais + pontos_ganhos

        if qualidade < 3:
            novo_intervalo = 1
            nova_facilidade = max(1.3, facilidade - 0.2)
        else:
            if intervalo == 0:
                novo_intervalo = 1
            elif intervalo == 1:
                novo_intervalo = 6
            else:
                novo_intervalo = round(intervalo * facilidade)
            nova_facilidade = facilidade + (0.1 - (5 - qualidade) * (0.08 + (5 - qualidade) * 0.02))
            nova_facilidade = max(1.3, nova_facilidade)

        # Atualizar palavra
        sql_update = f"""
            UPDATE {self.table}
            SET ultima_revisao = NOW(),
                intervalo = %s,
                facilidade = %s,
                pontos = %s
            WHERE termo = %s
        """
        cursor.execute(sql_update, (novo_intervalo, nova_facilidade, novo_pontos, termo.lower()))
        
        # Registrar revisão na tabela auxiliar
        sql_revisao = f"""
            INSERT INTO {self.revisoes_table} (palavra_id, qualidade, pontos_ganhos)
            VALUES (%s, %s, %s)
        """
        cursor.execute(sql_revisao, (palavra_id, qualidade, pontos_ganhos))
        
        conn.commit()
        cursor.close()
        conn.close()
        logger.info(f"Revisão registrada: {termo} (qualidade {qualidade}) -> +{pontos_ganhos} pontos (total: {novo_pontos})")
        return {
            "termo": termo,
            "novo_intervalo": novo_intervalo,
            "nova_facilidade": round(nova_facilidade, 2),
            "pontos_ganhos": pontos_ganhos,
            "pontos_total": novo_pontos
        }

    def atualizar(self, termo, nova_traducao=None, novo_contexto=None):
        """Atualiza a tradução e/ou o contexto de uma palavra existente."""
        conn = get_connection()
        cursor = conn.cursor()
        sets = []
        valores = []
        if nova_traducao is not None:
            sets.append("traducao = %s")
            valores.append(nova_traducao)
        if novo_contexto is not None:
            sets.append("contexto = %s")
            valores.append(novo_contexto)
        if not sets:
            return
        valores.append(termo.lower())
        sql = f"UPDATE {self.table} SET {', '.join(sets)} WHERE termo = %s"
        cursor.execute(sql, valores)
        conn.commit()
        cursor.close()
        conn.close()
        logger.info(f"Palavra atualizada: {termo}")

    def atualizar_notas(self, termo, notas):
        """Atualiza o campo notas de uma palavra."""
        conn = get_connection()
        cursor = conn.cursor()
        sql = f"UPDATE {self.table} SET notas = %s WHERE termo = %s"
        cursor.execute(sql, (notas, termo.lower()))
        conn.commit()
        cursor.close()
        conn.close()
        logger.info(f"Notas atualizadas para: {termo}")
        return {"mensagem": "Notas salvas"}

    # ---------- DECKS ----------
    def listar_decks(self):
        """Retorna todos os decks ordenados por nome."""
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM decks ORDER BY nome")
        decks = cursor.fetchall()
        cursor.close()
        conn.close()
        return decks

    def criar_deck(self, nome):
        """Cria um novo deck e retorna seu ID."""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO decks (nome) VALUES (%s)", (nome,))
        conn.commit()
        deck_id = cursor.lastrowid
        cursor.close()
        conn.close()
        logger.info(f"Deck criado: {nome} (ID {deck_id})")
        return deck_id

    def editar_deck(self, deck_id, novo_nome):
        """Atualiza o nome de um deck."""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE decks SET nome = %s WHERE id = %s", (novo_nome, deck_id))
        conn.commit()
        cursor.close()
        conn.close()
        logger.info(f"Deck {deck_id} renomeado para '{novo_nome}'")

    def excluir_deck(self, deck_id):
        """Exclui um deck e desvincula suas palavras (seta deck_id = NULL)."""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(f"UPDATE {self.table} SET deck_id = NULL WHERE deck_id = %s", (deck_id,))
        cursor.execute("DELETE FROM decks WHERE id = %s", (deck_id,))
        conn.commit()
        cursor.close()
        conn.close()
        logger.info(f"Deck {deck_id} excluído")

    def associar_deck(self, termo, deck_id):
        """Associa uma palavra existente a um deck (deck_id pode ser NULL)."""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(f"UPDATE {self.table} SET deck_id = %s WHERE termo = %s", (deck_id, termo.lower()))
        conn.commit()
        cursor.close()
        conn.close()
        logger.info(f"Palavra '{termo}' associada ao deck {deck_id}")

    def obter_deck_por_id(self, deck_id):
        """Retorna os dados de um deck a partir do seu ID."""
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM decks WHERE id = %s", (deck_id,))
        deck = cursor.fetchone()
        cursor.close()
        conn.close()
        return deck

    # ---------- DASHBOARD E ESTATÍSTICAS ----------
    def obter_dashboard(self, dias=30):
        """Retorna dados diários de revisões para gráficos."""
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        sql = f"""
            SELECT DATE(ultima_revisao) as data,
                   COUNT(*) as total_revisoes,
                   AVG(facilidade) as media_facilidade
            FROM {self.table}
            WHERE ultima_revisao >= DATE_SUB(CURDATE(), INTERVAL %s DAY)
            GROUP BY DATE(ultima_revisao)
            ORDER BY data ASC
        """
        cursor.execute(sql, (dias,))
        dados = cursor.fetchall()
        cursor.close()
        conn.close()
        for d in dados:
            d['data'] = d['data'].isoformat() if d['data'] else None
        return dados

    def obter_estatisticas(self):
        """Retorna total de palavras, revisadas hoje e média de facilidade."""
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute(f"SELECT COUNT(*) as total FROM {self.table}")
        total = cursor.fetchone()['total']

        cursor.execute(f"SELECT COUNT(*) as revisadas_hoje FROM {self.table} WHERE DATE(ultima_revisao) = CURDATE()")
        revisadas_hoje = cursor.fetchone()['revisadas_hoje']

        cursor.execute(f"SELECT AVG(facilidade) as media_facilidade FROM {self.table} WHERE facilidade IS NOT NULL")
        media_facilidade = cursor.fetchone()['media_facilidade'] or 0

        cursor.close()
        conn.close()
        return {
            "total_palavras": total,
            "revisadas_hoje": revisadas_hoje,
            "media_facilidade": round(media_facilidade, 2)
        }

    def obter_progresso(self):
        """Retorna pontos, streak, nível e total de revisões para gamificação."""
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        # Total de pontos (da tabela dicionario)
        cursor.execute(f"SELECT SUM(pontos) as total_pontos FROM {self.table}")
        total_pontos = cursor.fetchone()['total_pontos'] or 0

        # Total de revisões (da tabela revisoes)
        cursor.execute(f"SELECT COUNT(*) as total_revisoes FROM {self.revisoes_table}")
        total_revisoes = cursor.fetchone()['total_revisoes']

        # Streak (dias consecutivos com revisão até hoje)
        cursor.execute(f"""
            SELECT DISTINCT DATE(data_revisao) as data
            FROM {self.revisoes_table}
            ORDER BY data DESC
        """)
        datas = cursor.fetchall()
        streak = 0
        hoje = datetime.now().date()
        for i, row in enumerate(datas):
            data_revisao = row['data']
            if isinstance(data_revisao, datetime):
                data_revisao = data_revisao.date()
            if (hoje - data_revisao).days == i:
                streak += 1
            else:
                break

        cursor.close()
        conn.close()

        nivel = (total_pontos // 100) + 1
        pontos_para_proximo_nivel = 100 - (total_pontos % 100)

        return {
            "pontos_total": total_pontos,
            "total_revisoes": total_revisoes,
            "streak_atual": streak,
            "nivel": nivel,
            "pontos_para_proximo_nivel": pontos_para_proximo_nivel
        }

    def obter_estatisticas_por_deck(self):
        """Retorna para cada deck: nome, total de revisões, número de acertos (qualidade >= 3)."""
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        sql = """
            SELECT 
                d.id AS deck_id,
                d.nome AS deck_nome,
                COUNT(r.id) AS total_revisoes,
                SUM(CASE WHEN r.qualidade >= 3 THEN 1 ELSE 0 END) AS acertos
            FROM decks d
            LEFT JOIN dicionario p ON p.deck_id = d.id
            LEFT JOIN revisoes r ON r.palavra_id = p.id
            GROUP BY d.id, d.nome
            ORDER BY d.nome
        """
        cursor.execute(sql)
        resultados = cursor.fetchall()
        cursor.close()
        conn.close()
        return resultados

    def obter_evolucao_pontos(self, dias=30):
        """
        Retorna os pontos acumulados por dia (últimos `dias` dias).
        Os pontos são somados por data e acumulados ao longo do tempo.
        """
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        sql = """
            SELECT 
                DATE(r.data_revisao) AS data,
                SUM(r.pontos_ganhos) AS pontos_dia
            FROM revisoes r
            WHERE r.data_revisao >= DATE_SUB(CURDATE(), INTERVAL %s DAY)
            GROUP BY DATE(r.data_revisao)
            ORDER BY data ASC
        """
        cursor.execute(sql, (dias,))
        resultados = cursor.fetchall()
        cursor.close()
        conn.close()

        hoje = datetime.now().date()
        data_inicio = hoje - timedelta(days=dias-1)
        pontos_por_data = {row['data']: row['pontos_dia'] for row in resultados if row['data']}
        
        evolucao = []
        acumulado = 0
        for i in range(dias):
            data = data_inicio + timedelta(days=i)
            pontos = pontos_por_data.get(data, 0)
            acumulado += pontos
            evolucao.append({
                'data': data.strftime('%d/%m'),
                'pontos_acumulados': acumulado
            })
        return evolucao

    # ---------- NOVOS MÉTODOS PARA FRASES SALVAS E REGRAS GRAMATICAIS ----------
    def salvar_frase(self, frase, deck_id=None, palavra_origem=None):
        """Insere uma frase na tabela frases_salvas e retorna o ID."""
        conn = get_connection()
        cursor = conn.cursor()
        sql = f"""
            INSERT INTO {self.frases_table} (frase, deck_id, palavra_origem)
            VALUES (%s, %s, %s)
        """
        cursor.execute(sql, (frase, deck_id, palavra_origem))
        conn.commit()
        frase_id = cursor.lastrowid
        cursor.close()
        conn.close()
        logger.info(f"Frase salva (ID {frase_id})")
        return frase_id

    def listar_frases_por_deck(self, deck_id):
        """Retorna todas as frases associadas a um deck (aleatório)."""
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        sql = f"SELECT id, frase FROM {self.frases_table} WHERE deck_id = %s ORDER BY RAND()"
        cursor.execute(sql, (deck_id,))
        resultados = cursor.fetchall()
        cursor.close()
        conn.close()
        return resultados

    def obter_frases_por_deck_paginado(self, deck_id, pagina=1, por_pagina=10, busca=''):
        """Retorna frases de um deck com paginação e busca opcional."""
        offset = (pagina - 1) * por_pagina
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        if deck_id == 'none':
            sql = "SELECT id, frase FROM frases_salvas WHERE deck_id IS NULL"
            params = []
        elif deck_id == 'all':
            sql = "SELECT id, frase FROM frases_salvas"
            params = []
        else:
            sql = "SELECT id, frase FROM frases_salvas WHERE deck_id = %s"
            params = [deck_id]
        
        if busca:
            sql += " AND frase LIKE %s"
            params.append(f'%{busca}%')
        
        # Contagem total
        count_sql = f"SELECT COUNT(*) as total FROM ({sql}) AS sub"
        cursor.execute(count_sql, params)
        total = cursor.fetchone()['total']
        
        # Paginação
        sql += " ORDER BY id LIMIT %s OFFSET %s"
        params.extend([por_pagina, offset])
        cursor.execute(sql, params)
        frases = cursor.fetchall()
        cursor.close()
        conn.close()
        return frases, total

    def verificar_frase_em_qualquer_deck(self, frase):
        """Verifica se uma frase já existe em algum deck e retorna o nome do deck onde está."""
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT f.id, d.nome as deck_nome 
            FROM frases_salvas f
            LEFT JOIN decks d ON f.deck_id = d.id
            WHERE f.frase = %s
        """, (frase,))
        resultado = cursor.fetchone()
        cursor.close()
        conn.close()
        return resultado  # None se não existir, ou dicionário com deck_nome

    def adicionar_frase_revisao(self, frase_id, deck_id):
        """Marca uma frase para revisão (se ainda não estiver marcada)."""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            f"INSERT IGNORE INTO {self.frases_revisao_table} (frase_id, deck_id) VALUES (%s, %s)",
            (frase_id, deck_id)
        )
        conn.commit()
        cursor.close()
        conn.close()

    def obter_frases_revisao_por_deck(self, deck_param, limite=10):
        """Retorna frases pendentes de revisão de um deck."""
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        if deck_param == 'none':
            sql = """
                SELECT f.id, f.frase 
                FROM frases_revisao r
                JOIN frases_salvas f ON r.frase_id = f.id
                WHERE r.revisada = FALSE AND f.deck_id IS NULL
                ORDER BY r.data_adicao ASC LIMIT %s
            """
            cursor.execute(sql, (limite,))
        elif deck_param == 'all':
            sql = """
                SELECT f.id, f.frase 
                FROM frases_revisao r
                JOIN frases_salvas f ON r.frase_id = f.id
                WHERE r.revisada = FALSE
                ORDER BY r.data_adicao ASC LIMIT %s
            """
            cursor.execute(sql, (limite,))
        else:
            sql = """
                SELECT f.id, f.frase 
                FROM frases_revisao r
                JOIN frases_salvas f ON r.frase_id = f.id
                WHERE r.revisada = FALSE AND f.deck_id = %s
                ORDER BY r.data_adicao ASC LIMIT %s
            """
            cursor.execute(sql, (deck_param, limite))
        frases = cursor.fetchall()
        cursor.close()
        conn.close()
        return frases

    def marcar_frase_revisada(self, frase_id):
        """Marca uma frase como já revista."""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(f"UPDATE {self.frases_revisao_table} SET revisada = TRUE WHERE frase_id = %s", (frase_id,))
        conn.commit()
        cursor.close()
        conn.close()

    def adicionar_regra(self, padrao, sugestao, explicacao=None):
        """Insere uma nova regra gramatical e retorna o ID."""
        conn = get_connection()
        cursor = conn.cursor()
        sql = f"""
            INSERT INTO {self.regras_table} (padrao, sugestao, explicacao)
            VALUES (%s, %s, %s)
        """
        cursor.execute(sql, (padrao, sugestao, explicacao))
        conn.commit()
        regra_id = cursor.lastrowid
        cursor.close()
        conn.close()
        logger.info(f"Regra gramatical adicionada (ID {regra_id})")
        return regra_id

    def listar_regras(self):
        """Retorna todas as regras gramaticais (ativas e inativas), ordenadas por ID decrescente."""
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        sql = f"SELECT * FROM {self.regras_table} ORDER BY id DESC"
        cursor.execute(sql)
        resultados = cursor.fetchall()
        cursor.close()
        conn.close()
        return resultados

    def listar_regras_ativas(self):
        """Retorna apenas as regras com ativo = 1."""
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        sql = f"SELECT * FROM {self.regras_table} WHERE ativo = 1"
        cursor.execute(sql)
        resultados = cursor.fetchall()
        cursor.close()
        conn.close()
        return resultados