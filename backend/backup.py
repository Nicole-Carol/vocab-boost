import subprocess
import os
from datetime import datetime
from config import MYSQL_HOST, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DATABASE

# Pasta onde os backups serão salvos
BACKUP_DIR = "backups"
os.makedirs(BACKUP_DIR, exist_ok=True)

# Nome do arquivo com timestamp
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
filename = f"{BACKUP_DIR}/backup_{MYSQL_DATABASE}_{timestamp}.sql"

# ⚠️ Substitua pelo caminho que você encontrou (sem .exe)
MYSQLDUMP_PATH = r"C:\Program Files\MySQL\MySQL Server 8.0\bin\mysqldump"

# Comando (usa lista para não exibir a senha em logs)
cmd = [
    MYSQLDUMP_PATH,
    "-h", MYSQL_HOST,
    "-u", MYSQL_USER,
    f"-p{MYSQL_PASSWORD}",
    MYSQL_DATABASE
]

print(f"🔧 Executando backup: {filename}")
try:
    with open(filename, "w", encoding="utf-8") as outfile:
        subprocess.run(cmd, stdout=outfile, check=True)
    print(f"✅ Backup salvo em: {filename}")
except subprocess.CalledProcessError as e:
    print(f"❌ Erro no backup: {e}")
except FileNotFoundError:
    print(f"❌ mysqldump não encontrado em {MYSQLDUMP_PATH}")