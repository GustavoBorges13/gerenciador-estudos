import sys
import signal
import os
import platform
from pathlib import Path

from PySide6.QtWidgets import QApplication

# As importações agora são relativas ao pacote
from gerenciador_estudos.config import DEBUG_MODE
from gerenciador_estudos.logic import setup_directories
from gerenciador_estudos.widgets import JanelaPrincipal

def setup_qt_environment():
    """
    Configura as variáveis de ambiente essenciais para o Qt ANTES da inicialização,
    replicando perfeitamente a configuração do ambiente HyDE do usuário e garantindo
    que os plugins de estilo sejam encontrados.
    """
    if platform.system() != "Linux":
        return

    # 1. Define o backend de plataforma para Wayland.
    os.environ.setdefault('QT_QPA_PLATFORM', 'wayland')

    # 2. Define o plugin de tema para 'qt6ct'.
    os.environ.setdefault('QT_QPA_PLATFORMTHEME', 'qt6ct')
    
    # 3. Define o estilo para 'kvantum'.
    os.environ.setdefault('QT_STYLE_OVERRIDE', 'kvantum')

    # 4. A CORREÇÃO FINAL E MAIS IMPORTANTE:
    # Diz ao Qt onde encontrar os plugins de estilo, como o Kvantum.
    # No Arch Linux, os plugins do Qt6 estão geralmente em /usr/lib/qt6/plugins.
    # Adicionamos este caminho à variável QT_PLUGIN_PATH.
    plugin_path = "/usr/lib/qt6/plugins"
    os.environ.setdefault('QT_PLUGIN_PATH', plugin_path)


def main():
    """Ponto de entrada principal da aplicação."""

    # Executa a configuração de ambiente ANTES de criar a QApplication.
    setup_qt_environment()

    app = QApplication(sys.argv)

    if DEBUG_MODE:
        print("--- MODO DE DEBUG ATIVADO ---")

    setup_directories()
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    janela = JanelaPrincipal()
    janela.show()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()