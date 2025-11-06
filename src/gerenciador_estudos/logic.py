import os
import hashlib
import shutil
import subprocess
import webbrowser
import platform
from pathlib import Path

import fitz
from PySide6.QtWidgets import QMessageBox

from gerenciador_estudos.config import debug_log, PDF_DIR, THUMB_DIR, APP_DATA_DIR, CACHE_DIR # 

def setup_directories():
    """Garante que todos os diretórios necessários existam."""
    debug_log("Executando setup_directories...")
    APP_DATA_DIR.mkdir(parents=True, exist_ok=True)
    THUMB_DIR.mkdir(parents=True, exist_ok=True)
    PDF_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Diretório de dados: {APP_DATA_DIR}")
    print(f"Diretório de cache: {CACHE_DIR}")

def get_stable_hash(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()[:16]

def gerar_thumbnail(pdf_input_path, thumb_output_path):
    try:
        if not os.path.exists(pdf_input_path):
            debug_log(f"[ERRO THUMB] Arquivo PDF de entrada não existe: {pdf_input_path}")
            return None
        with fitz.open(pdf_input_path) as doc:
            page = doc.load_page(0)
            zoom = 1.5
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat)
            pix.save(thumb_output_path)
        debug_log(f"Thumbnail gerado com sucesso para: {thumb_output_path}")
        return str(thumb_output_path)
    except Exception as e:
        print(f"Erro ao gerar thumbnail para '{pdf_input_path}': {e}")
    return None

def abrir_pdf_na_pagina(caminho_pdf, pagina):
    """Função multiplataforma para abrir um PDF em uma página específica."""
    debug_log(f"Tentando abrir PDF: '{caminho_pdf}' na página {pagina}")
    if not os.path.exists(caminho_pdf):
        QMessageBox.critical(None, "Erro", f"O arquivo PDF não foi encontrado no cache:\n{caminho_pdf}"); return

    system = platform.system()
    try:
        if system == "Windows":
            os.startfile(caminho_pdf)
            return
        elif system == "Darwin":
            uri = Path(caminho_pdf).as_uri() + f'#page={pagina}'
            webbrowser.open(uri)
            return
        elif system == "Linux":
            try:
                subprocess.Popen(['okular', '--page', str(pagina), caminho_pdf]); return
            except FileNotFoundError: pass
            try:
                subprocess.Popen(['xdg-open', caminho_pdf]); return
            except FileNotFoundError:
                debug_log("Nem Okular nem xdg-open encontrados. Usando fallback...")
    except Exception as e:
        debug_log(f"Erro ao tentar abrir PDF com método nativo: {e}")

    try:
        uri = Path(caminho_pdf).as_uri() + f'#page={pagina}'
        webbrowser.open(uri)
    except Exception as e:
        QMessageBox.critical(None, "Erro", f"Não foi possível abrir o PDF:\n{e}")