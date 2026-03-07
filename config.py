import os

# --- TESSERACT OCR ---
# Baixe e instale em: https://github.com/UB-Mannheim/tesseract/wiki
# Após instalar, verifique se o caminho abaixo está correto.
TESSERACT_PATH = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# --- PAUSAS (em segundos) ---
PAUSA_CURTA = 0.8  # pequena pausa após digitar/pressionar teclas
TIMEOUT = 20  # tempo máximo esperando um elemento aparecer na tela
INTERVALO = 0.5  # intervalo entre cada verificação de tela

# --- PASTAS ---
PASTA_ENTRADA = os.path.join("dados", "entrada")
PASTA_SAIDA = os.path.join("dados", "saida")
PASTA_BOTOES = os.path.join("capturas", "botoes")
PASTA_BOTOES_COLAB = os.path.join("capturas", "botoes_colab")
PASTA_PRINTS = os.path.join("capturas", "screenshots")
PASTA_LOGS = "logs"

# --- ARQUIVOS DE DADOS ---
ARQUIVO_EMPRESAS = os.path.join(PASTA_ENTRADA, "empresas.csv")
ARQUIVO_EVENTOS = os.path.join(PASTA_ENTRADA, "eventos.csv")
