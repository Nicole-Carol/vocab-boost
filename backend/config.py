import os
from dotenv import load_dotenv

load_dotenv()

MYSQL_HOST = "localhost"
MYSQL_USER = "root"
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD")
MYSQL_DATABASE = "meu_banco"

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")