import pytesseract
from PIL import Image
from config import TESSERACT_PATH

# Aponta o pytesseract para o executável do Tesseract instalado no Windows
pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH


def ler_texto(caminho_imagem):
    """
    Lê o texto de uma imagem usando OCR e retorna como string.

    Parâmetro:
        caminho_imagem: caminho completo para o arquivo .png

    lang="por" usa o dicionário de Português.
    Para instalar: no instalador do Tesseract, marque "Portuguese" em Additional language data.
    """
    imagem = Image.open(caminho_imagem)
    texto  = pytesseract.image_to_string(imagem, lang="por")
    return texto.strip()
