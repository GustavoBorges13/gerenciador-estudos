import os
import json
from pathlib import Path
import shutil
import platform

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
                               QScrollArea, QInputDialog, QFileDialog, QMessageBox,
                               QMenu, QDialog, QDialogButtonBox, QFormLayout,
                               QLineEdit, QSpinBox, QApplication)
from PySide6.QtGui import QIcon, QCursor, QPalette, QAction, QFontMetrics
from PySide6.QtCore import (QSize, Qt, QEvent, QPoint, QPropertyAnimation, QEasingCurve,
                            QAbstractAnimation, QThread, Signal)

# Importações dos nossos módulos
from .config import (STATUS_CONFIG, JSON_PATH, THUMB_DIR, PDF_DIR, debug_log)
from .logic import (get_stable_hash, gerar_thumbnail, abrir_pdf_na_pagina)


# --- WORKER PARA THREADING ---
class ThumbnailWorker(QThread):
    finished = Signal(QPushButton, str)
    def __init__(self, botao, pdf_input_path, thumb_output_path):
        super().__init__()
        self.botao = botao
        self.pdf_input_path = pdf_input_path
        self.thumb_output_path = thumb_output_path
    def run(self):
        caminho_gerado = gerar_thumbnail(self.pdf_input_path, self.thumb_output_path)
        if caminho_gerado: self.finished.emit(self.botao, caminho_gerado)

# --- WIDGETS PERSONALIZADOS ---
class EditarLivroDialog(QDialog):
    def __init__(self, parent=None, titulo_atual="", pagina_atual=1):
        super().__init__(parent);self.setWindowTitle("Editar Livro");self.titulo_edit = QLineEdit(titulo_atual);self.pagina_spinbox = QSpinBox();self.pagina_spinbox.setMinimum(1); self.pagina_spinbox.setMaximum(99999);self.pagina_spinbox.setValue(pagina_atual);font_metrics = self.titulo_edit.fontMetrics();text_width = font_metrics.horizontalAdvance(titulo_atual);self.titulo_edit.setMinimumWidth(text_width + 50);layout = QFormLayout(self);layout.addRow("Novo Título:", self.titulo_edit);layout.addRow("Página Atual:", self.pagina_spinbox);self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel);self.button_box.accepted.connect(self.accept); self.button_box.rejected.connect(self.reject);layout.addWidget(self.button_box);self.adjustSize()
    def get_dados(self): return self.titulo_edit.text(), self.pagina_spinbox.value()
    @staticmethod
    def run(parent, titulo_atual, pagina_atual):
        dialog = EditarLivroDialog(parent, titulo_atual, pagina_atual)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            novo_titulo, nova_pagina = dialog.get_dados()
            if novo_titulo: return novo_titulo, nova_pagina, True
        return None, None, False

class BotaoLivro(QPushButton):
    def __init__(self, d, l, jp, *a, **k):super().__init__(*a, **k);self.disciplina=d;self.livro=l;self.janela_principal=jp;self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu);self.customContextMenuRequested.connect(self.mostrar_menu_contexto);self.default_icon_size=QSize(120,170);self.hover_icon_size=QSize(130,185);self.setStyleSheet("QPushButton { border: 2px solid transparent; background-color: transparent; border-radius: 5px; }");self.setIconSize(self.default_icon_size);self.zoom_in_animation=QPropertyAnimation(self,b"iconSize");self.zoom_in_animation.setDuration(150);self.zoom_in_animation.setStartValue(self.default_icon_size);self.zoom_in_animation.setEndValue(self.hover_icon_size);self.zoom_in_animation.setEasingCurve(QEasingCurve.OutQuad);self.zoom_out_animation=QPropertyAnimation(self,b"iconSize");self.zoom_out_animation.setDuration(150);self.zoom_out_animation.setStartValue(self.hover_icon_size);self.zoom_out_animation.setEndValue(self.default_icon_size);self.zoom_out_animation.setEasingCurve(QEasingCurve.OutQuad)
    def enterEvent(self, e):
        if self.zoom_out_animation.state()==QAbstractAnimation.State.Running:self.zoom_out_animation.stop()
        self.zoom_in_animation.start();super().enterEvent(e)
    def leaveEvent(self, e):
        if self.zoom_in_animation.state()==QAbstractAnimation.State.Running:self.zoom_in_animation.stop()
        self.zoom_out_animation.start();super().leaveEvent(e)
    def mostrar_menu_contexto(self, pos):menu=QMenu();a_e=QAction("Editar Livro",self);a_e.triggered.connect(self.editar);menu.addAction(a_e);a_r=QAction("Remover Livro",self);a_r.triggered.connect(self.remover);menu.addAction(a_r);menu.addSeparator();s_s=QMenu("Marcar como...",self);a_l=QAction("Em Leitura",self);a_l.triggered.connect(lambda:self.definir_status("lendo"));s_s.addAction(a_l);a_c=QAction("Concluído",self);a_c.triggered.connect(lambda:self.definir_status("concluido"));s_s.addAction(a_c);a_nl=QAction("Não Lido",self);a_nl.triggered.connect(lambda:self.definir_status("nao_lido"));s_s.addAction(a_nl);menu.addMenu(s_s);menu.exec(self.mapToGlobal(pos))
    def editar(self):
        nt, np, ok = EditarLivroDialog.run(self,self.livro['titulo'],self.livro['pagina_atual'])
        if ok:self.livro['titulo']=nt;self.livro['pagina_atual']=np;self.janela_principal.salvar_e_recarregar()
    def remover(self):
        if QMessageBox.question(self,"Confirmar Remoção",f"Tem certeza que deseja remover o livro '{self.livro['titulo']}'?",QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No)==QMessageBox.StandardButton.Yes:
            caminho_cache_pdf=Path(self.livro.get("caminho_cache",""));caminho_original=self.livro.get("caminho_original","");hash_id=get_stable_hash(caminho_original);caminho_cache_thumb=THUMB_DIR/f"{Path(caminho_original).stem}_{hash_id}.png"
            try:
                if caminho_cache_pdf.exists():caminho_cache_pdf.unlink()
                if caminho_cache_thumb.exists():caminho_cache_thumb.unlink()
            except Exception as e:print(f"Erro ao remover arquivos do cache: {e}")
            self.disciplina['livros'].remove(self.livro);self.janela_principal.salvar_e_recarregar()
    def definir_status(self,ns):self.livro['status']=ns;self.janela_principal.salvar_e_recarregar()

class ScrollAreaArrastavel(QScrollArea):
    def __init__(self,*a,**k):super().__init__(*a,**k);self.setWidgetResizable(True);self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff);self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff);self.is_dragging=False;self.last_mouse_pos=QPoint();self.drag_start_pos=QPoint();self.setCursor(QCursor(Qt.CursorShape.OpenHandCursor));self.gradient_overlay=QWidget(self);self.gradient_overlay.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents);self.update_gradient_stylesheet()
    def update_gradient_stylesheet(self):bg=self.palette().color(QPalette.ColorRole.Window);ct=f"rgba({bg.red()},{bg.green()},{bg.blue()},0)";cs=f"rgba({bg.red()},{bg.green()},{bg.blue()},255)";s=f"""QWidget{{background-color:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 {ct},stop:1 {cs});}}""";self.gradient_overlay.setStyleSheet(s)
    def resizeEvent(self,e):super().resizeEvent(e);bh=200;gw=50;y=(self.height()-bh)/2.0;self.gradient_overlay.setGeometry(self.width()-gw,int(y),gw,bh);self.gradient_overlay.raise_()
    def eventFilter(self,w,e):
        if isinstance(w,QPushButton):
            if e.type()==QEvent.Type.MouseButtonPress:self.mousePressEvent(e);return True
            if e.type()==QEvent.Type.MouseMove:self.mouseMoveEvent(e);return True
            if e.type()==QEvent.Type.MouseButtonRelease:self.mouseReleaseEvent(e, cw=w);return True
        return super().eventFilter(w,e)
    def mousePressEvent(self,e):
        if e.button()==Qt.MouseButton.LeftButton:self.is_dragging=True;self.drag_start_pos=e.globalPosition().toPoint();self.last_mouse_pos=e.globalPosition().toPoint();self.setCursor(QCursor(Qt.CursorShape.ClosedHandCursor))
    def mouseMoveEvent(self,e):
        if self.is_dragging:cp=e.globalPosition().toPoint();d=cp-self.last_mouse_pos;self.last_mouse_pos=cp;hb=self.horizontalScrollBar();hb.setValue(hb.value()-d.x())
    def mouseReleaseEvent(self,e,cw=None):
        if e.button()==Qt.MouseButton.LeftButton and self.is_dragging:
            self.is_dragging=False;self.setCursor(QCursor(Qt.CursorShape.OpenHandCursor));rp=e.globalPosition().toPoint();dist=(rp-self.drag_start_pos).manhattanLength()
            if cw and dist<QApplication.styleHints().startDragDistance():cw.click()

# --- CLASSE DA INTERFACE PRINCIPAL ---
class JanelaPrincipal(QWidget):
    def __init__(self):
        super().__init__()
        # --- CARREGANDO O ÍCONE DA FORMA CORRETA ---
        # Constrói o caminho para o ícone a partir da localização deste arquivo
        icon_path = Path(__file__).parent / "assets" / "icone.ico"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))
        
        self.dados = {}
        self.thumbnail_workers = []
        self.init_ui()
        self.carregar_dados()

    def init_ui(self):
        # --- LÓGICA DE DETECÇÃO DE AMBIENTE PARA UI PERSONALIZADA ---
        window_title = 'Gerenciador de Estudos'
        window_height = 800
        window_width = 400

        if platform.system() == "Linux" and os.getenv('XDG_CURRENT_DESKTOP') == 'Hyprland':
            debug_log("Detectado ambiente Hyprland. Aplicando UI específica.")
            window_title = 'Gerenciador de Estudos (dialog)'
            window_height = 900
            window_width = 400

        self.setWindowTitle(window_title)
        self.resize(window_width, window_height)
        self.setMinimumSize(window_width, window_height)

        self.main_layout = QVBoxLayout(self)
        btn = QPushButton("＋ Adicionar Nova Disciplina")
        btn.clicked.connect(self.adicionar_disciplina)
        self.main_layout.addWidget(btn)

        self.scroll_area_main = QScrollArea()
        self.scroll_area_main.setWidgetResizable(True)
        self.scroll_area_main.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.main_layout.addWidget(self.scroll_area_main)

    def set_thumbnail_icon(self, botao, caminho_imagem):
        if caminho_imagem and os.path.exists(caminho_imagem):
            botao.setIcon(QIcon(caminho_imagem))

    def carregar_dados(self):
        debug_log(f"Tentando carregar dados de: {JSON_PATH}")
        try:
            with open(JSON_PATH, 'r', encoding='utf-8') as f:
                self.dados = json.load(f)
            debug_log("Arquivo data.json carregado com sucesso.")
        except (FileNotFoundError, json.JSONDecodeError):
            debug_log("Arquivo data.json não encontrado ou inválido. Iniciando com dados vazios.")
            self.dados = {"disciplinas": []}
        self.exibir_disciplinas()

    def salvar_e_recarregar(self):
        debug_log(f"Salvando dados em: {JSON_PATH}")
        with open(JSON_PATH, 'w', encoding='utf-8') as f:
            json.dump(self.dados, f, indent=2, ensure_ascii=False)
        self.exibir_disciplinas()

    def exibir_disciplinas(self):
        self.thumbnail_workers.clear()
        old_widget = self.scroll_area_main.takeWidget()
        if old_widget is not None:
            old_widget.deleteLater()

        content_widget = QWidget()
        self.content_layout = QVBoxLayout(content_widget)
        self.content_layout.setContentsMargins(10, 10, 10, 10)
        self.content_layout.setSpacing(15)
        self.scroll_area_main.setWidget(content_widget)

        for disciplina in self.dados['disciplinas']:
            self.criar_widgets_disciplina(disciplina)
        
        self.content_layout.addStretch()

    def criar_widgets_disciplina(self, disciplina):
        # Header da disciplina (Nome, Editar, Remover)
        header_layout = QHBoxLayout()
        label_nome = QLabel(f"<b>{disciplina['nome']}</b>")
        label_nome.setStyleSheet("font-size: 14pt;")
        btn_editar = QPushButton("Editar")
        btn_editar.setFixedSize(60, 25)
        btn_editar.clicked.connect(lambda checked, d=disciplina: self.editar_disciplina(d))
        btn_remover = QPushButton("Remover")
        btn_remover.setFixedSize(70, 25)
        btn_remover.clicked.connect(lambda checked, d=disciplina: self.remover_disciplina(d))
        header_layout.addWidget(label_nome)
        header_layout.addStretch()
        header_layout.addWidget(btn_editar)
        header_layout.addWidget(btn_remover)
        self.content_layout.addLayout(header_layout)

        # Scroll Area para os livros
        scroll_area_livros = ScrollAreaArrastavel()
        scroll_area_livros.setFixedHeight(250)
        scroll_area_livros.setStyleSheet("QScrollArea { border: none; }")
        
        container_livros_widget = QWidget()
        layout_livros = QHBoxLayout(container_livros_widget)

        for livro in disciplina['livros']:
            self.criar_widget_livro(layout_livros, scroll_area_livros, disciplina, livro)
        
        # Botão de adicionar livro
        self.criar_widget_adicionar_livro(layout_livros, disciplina)

        scroll_area_livros.setWidget(container_livros_widget)
        self.content_layout.addWidget(scroll_area_livros)

    def criar_widget_livro(self, layout, parent_scroll, disciplina, livro):
        livro_widget_container = QWidget()
        livro_widget_container.setFixedWidth(140)
        v_layout = QVBoxLayout(livro_widget_container)
        v_layout.setContentsMargins(0, 0, 0, 0)
        v_layout.setSpacing(4)
        
        btn_livro = BotaoLivro(disciplina, livro, self)
        btn_livro.setFixedSize(140, 200)

        caminho_original = livro.get("caminho_original", "")
        hash_id = get_stable_hash(caminho_original)
        nome_base = Path(caminho_original).stem
        caminho_thumb = THUMB_DIR / f"{nome_base}_{hash_id}.png"
        caminho_cache = livro.get("caminho_cache")

        if not caminho_cache or not Path(caminho_cache).exists():
            debug_log(f"Alerta: Caminho de cache para '{livro['titulo']}' não encontrado: '{caminho_cache}'")

        if caminho_thumb.exists():
            btn_livro.setIcon(QIcon(str(caminho_thumb)))
        elif caminho_cache and Path(caminho_cache).exists():
            worker = ThumbnailWorker(btn_livro, caminho_cache, str(caminho_thumb))
            worker.finished.connect(self.set_thumbnail_icon)
            self.thumbnail_workers.append(worker)
            worker.start()

        btn_livro.setToolTip(f"{livro['titulo']}\nPágina: {livro['pagina_atual']}")
        btn_livro.clicked.connect(lambda checked, p=caminho_cache, pg=livro['pagina_atual']: abrir_pdf_na_pagina(p, pg))
        btn_livro.installEventFilter(parent_scroll)

        status = livro.get('status', 'nao_lido')
        cfg = STATUS_CONFIG[status]
        label_status = QLabel(f"<b>{cfg['texto']}</b>")
        label_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label_status.setStyleSheet(f"color: {cfg['cor']}; font-size: 10pt;")
        
        v_layout.addWidget(btn_livro)
        v_layout.addWidget(label_status)
        layout.addWidget(livro_widget_container)
    
    def criar_widget_adicionar_livro(self, layout, disciplina):
        container = QWidget()
        container.setFixedWidth(140)
        v_layout = QVBoxLayout(container)
        v_layout.setContentsMargins(0, 0, 0, 0)
        v_layout.setSpacing(4)

        btn_add = QPushButton("+")
        btn_add.setFixedSize(140, 200)
        btn_add.setStyleSheet("font-size: 48pt; color: grey; border-radius: 5px;")
        btn_add.clicked.connect(lambda checked, d=disciplina: self.adicionar_livro(d))
        
        label_vazia = QLabel("")
        v_layout.addWidget(btn_add)
        v_layout.addWidget(label_vazia)
        layout.addWidget(container)

    def _get_text_from_dialog(self, title, label, initial_text=""):
        dialog = QInputDialog(self); dialog.setWindowTitle(title); dialog.setLabelText(label); dialog.setTextValue(initial_text); dialog.resize(500, 100); ok = dialog.exec(); text = dialog.textValue(); return text, ok

    def adicionar_disciplina(self):
        n,ok=self._get_text_from_dialog("Nova Disciplina","Nome da disciplina:")
        if ok and n:self.dados['disciplinas'].append({"nome":n,"livros":[]});self.salvar_e_recarregar()
    
    def editar_disciplina(self, d):
        nn,ok=self._get_text_from_dialog("Editar Disciplina","Novo nome:",initial_text=d['nome'])
        if ok and nn:d['nome']=nn;self.salvar_e_recarregar()
    
    def remover_disciplina(self, d):
        if QMessageBox.question(self,"Confirmar Remoção",f"Tem certeza que deseja remover a disciplina '{d['nome']}' e todos os seus livros?",QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No)==QMessageBox.StandardButton.Yes:
            for livro in d['livros']:
                caminho_cache_pdf=Path(livro.get("caminho_cache",""));caminho_original=livro.get("caminho_original","");hash_id=get_stable_hash(caminho_original);caminho_cache_thumb=THUMB_DIR/f"{Path(caminho_original).stem}_{hash_id}.png"
                try:
                    if caminho_cache_pdf.exists():caminho_cache_pdf.unlink()
                    if caminho_cache_thumb.exists():caminho_cache_thumb.unlink()
                except Exception as e:print(f"Erro ao remover arquivos do cache: {e}")
            self.dados['disciplinas'].remove(d);self.salvar_e_recarregar()

    def adicionar_livro(self, disciplina):
        caminhos_selecionados, _ = QFileDialog.getOpenFileNames(self, "Selecionar um ou mais PDFs", "", "Arquivos PDF (*.pdf)")
        if not caminhos_selecionados: return

        livros_adicionados = 0
        for caminho_original_str in caminhos_selecionados:
            try:
                source_path = Path(caminho_original_str)
                titulo = source_path.stem
                hash_id = get_stable_hash(caminho_original_str)
                unique_filename = f"{source_path.stem}_{hash_id}{source_path.suffix}"
                dest_path = PDF_DIR / unique_filename

                if not dest_path.exists():
                    shutil.copy2(source_path, dest_path)
                
                caminho_cache_absoluto = os.path.abspath(dest_path)
                debug_log(f"Caminho do cache a ser salvo no JSON: {caminho_cache_absoluto}")
                
                novo_livro = {"titulo":titulo,"caminho_original":caminho_original_str,"caminho_cache":caminho_cache_absoluto,"pagina_atual":1,"status":"nao_lido"}
                disciplina['livros'].append(novo_livro)
                livros_adicionados += 1
            except Exception as e:
                QMessageBox.critical(self,"Erro ao Copiar Arquivo",f"Não foi possível salvar o PDF no cache:\n{caminho_original_str}\n\nErro: {e}")
        
        if livros_adicionados > 0: self.salvar_e_recarregar()