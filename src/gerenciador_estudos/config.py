import sys
import os
import platform
from pathlib import Path

# --- MODO DE DEBUG ---
# Ativa o modo de depuração se --debug for passado como argumento na linha de comando
DEBUG_MODE = "--debug" in sys.argv

def debug_log(message):
    """Imprime mensagens de log apenas se o DEBUG_MODE estiver ativo."""
    if DEBUG_MODE:
        print(f"[DEBUG] {message}")

# --- DETECÇÃO DO AMBIENTE (A SOLUÇÃO DEFINITIVA) ---
def is_windows_store_app():
    """
    Verifica de forma definitiva se o script está rodando na versão da Microsoft Store,
    verificando a existência do diretório do pacote Python dentro de %LOCALAPPDATA%\\Packages.
    """
    if platform.system() != "Windows":
        return False

    # 1. Pega o caminho base de %LOCALAPPDATA%
    local_appdata_str = os.getenv('LOCALAPPDATA')
    if not local_appdata_str:
        return False # Não podemos continuar se a variável não existir

    # 2. Constrói o caminho para a pasta "Packages", como você sugeriu.
    packages_path = Path(local_appdata_str) / "Packages"
    debug_log(f"Verificando a existência da pasta de pacotes da Store em: {packages_path}")

    # 3. Verifica se a pasta "Packages" realmente existe.
    if not packages_path.is_dir():
        debug_log("Pasta 'Packages' não encontrada. Assumindo instalação normal.")
        return False

    # 4. Procura por um diretório que contenha "PythonSoftwareFoundation" dentro de "Packages".
    try:
        for dirname in os.listdir(packages_path):
            # Procura de forma case-insensitive por segurança
            if "pythonsoftwarefoundation" in dirname.lower():
                debug_log(f"Diretório do pacote Python da Store encontrado: {dirname}")
                return True # Encontramos! É a versão da loja.
    except FileNotFoundError:
        return False # Se não conseguir ler o diretório

    # Se o loop terminar sem encontrar, não é a versão da loja.
    debug_log("Nenhum diretório do pacote Python da Store foi encontrado em 'Packages'.")
    return False

# --- LÓGICA DE DEFINIÇÃO DE CAMINHOS ---
def get_app_data_dir():
    """Retorna o diretório de dados apropriado, lidando com o sandbox do Windows."""
    system = platform.system()
    debug_log(f"Sistema Operacional Detectado: {system}")

    if is_windows_store_app():
        debug_log("!! ATENÇÃO: Detectada versão Python da Microsoft Store !!")
        debug_log("Forçando o uso de um diretório local para evitar o sandbox.")
        path = Path.cwd() / "estudos_data"
    elif system == "Windows":
        path = Path.home() / "AppData" / "Roaming" / "gerenciador_estudos"
    elif system == "Darwin": # macOS
        path = Path.home() / "Library" / "Application Support" / "gerenciador_estudos"
    elif system == "Linux":
        xdg_data = os.getenv('XDG_DATA_HOME', Path.home() / ".local" / "share")
        path = Path(xdg_data) / "gerenciador_estudos"
    else:
        path = Path.cwd() / "estudos_data" # Fallback
        
    debug_log(f"Caminho de DADOS definido como: {path}")
    return path

def get_cache_dir():
    """Retorna o diretório de cache apropriado, lidando com o sandbox do Windows."""
    if is_windows_store_app():
        path = Path.cwd() / "estudos_data" / "cache"
    elif platform.system() == "Windows":
        path = Path.home() / "AppData" / "Local" / "gerenciador_estudos_cache"
    elif platform.system() == "Darwin": # macOS
        path = Path.home() / "Library" / "Caches" / "gerenciador_estudos"
    elif platform.system() == "Linux":
        xdg_cache = os.getenv('XDG_CACHE_HOME', Path.home() / ".cache")
        path = Path(xdg_cache) / "gerenciador_estudos"
    else:
        path = Path.cwd() / "estudos_data" / "cache" # Fallback

    debug_log(f"Caminho de CACHE definido como: {path}")
    return path

# --- CONSTANTES GLOBAIS ---
APP_DATA_DIR = get_app_data_dir()
CACHE_DIR = get_cache_dir()
THUMB_DIR = CACHE_DIR / "thumbs"
PDF_DIR = CACHE_DIR / "pdfs"
JSON_PATH = APP_DATA_DIR / "data.json"
STATUS_CONFIG = {
    "nao_lido":{"texto":"Não Lido","cor":"grey"},
    "lendo":{"texto":"Em Leitura","cor":"#3498db"},
    "concluido":{"texto":"Concluído","cor":"#2ecc71"}
}