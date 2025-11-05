import sys
import json
import subprocess
import os
import signal
import datetime # Para a data de atualização

from pdf2image import convert_from_path

from PySide6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                               QLabel, QPushButton, QScrollArea, QInputDialog,
                               QFileDialog, QMessageBox, QMenu)
from PySide6.QtGui import QIcon, QCursor, QPalette, QAction
from PySide6.QtCore import QSize, Qt, QEvent, QPoint, QPropertyAnimation, QEasingCurve, QAbstractAnimation

# --- CONFIGURAÇÃO DE STATUS ---
STATUS_CONFIG = {"nao_lido":{"texto":"Não Lido","cor":"grey"},"lendo":{"texto":"Em Leitura","cor":"#3498db"},"concluido":{"texto":"Concluído","cor":"#2ecc71"}}

# --- FUNÇÕES DE LÓGICA (BACK-END) ---

### MUDANÇA: Função para abrir PDF de forma compatível com vários sistemas ###
def abrir_pdf_compativel(caminho_pdf):
    """Abre um arquivo PDF usando o visualizador padrão do sistema operacional."""
    try:
        if sys.platform == "win32":
            os.startfile(caminho_pdf)
        elif sys.platform == "darwin": # macOS
            subprocess.Popen(["open", caminho_pdf])
        else: # linux e outros
            subprocess.Popen(["xdg-open", caminho_pdf])
    except Exception as e:
        print(f"Não foi possível abrir o PDF: {e}")
        # Opcional: Mostrar uma QMessageBox de erro para o usuário
        # msg = QMessageBox()
        # msg.setIcon(QMessageBox.Critical)
        # msg.setText(f"Não foi possível abrir o PDF.\nVerifique se você tem um leitor de PDF instalado.\n\nErro: {e}")
        # msg.setWindowTitle("Erro ao Abrir PDF")
        # msg.exec()

def gerar_dados_simulados(c,p):
    if os.path.exists(c):return
    print("Gerando dados de simulação...")
    if not os.path.exists(p):print(f"ERRO: O PDF de exemplo '{p}' não foi encontrado.");sys.exit(1)
    d=[{"nome":"Exemplo de Tópico","livros":[{"titulo":f"Livro de Exemplo - Vol. {i+1}","caminho_pdf":p,"pagina_atual":10*(i+1),"status":"lendo"} for i in range(3)]}]
    with open(c,'w',encoding='utf-8') as f:json.dump({"topicos":d},f,indent=2,ensure_ascii=False) # MUDANÇA: 'disciplinas' -> 'topicos'

def gerar_thumbnail(p,t):
    n=os.path.basename(p).replace('.pdf','');c=os.path.join(t,f"{n}_{hash(p)}.png")
    if not os.path.exists(t):os.makedirs(t)
    if not os.path.exists(c):
        try:
            i=convert_from_path(p,first_page=1,last_page=1,size=(400,None))
            if i:i[0].save(c,'PNG');return c
        except Exception as e:print(f"Erro ao gerar thumbnail: {e}");return None
    return c

# --- WIDGETS PERSONALIZADOS ---

class BotaoLivro(QPushButton):
    def __init__(self, topico, livro, janela_principal, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.topico = topico; self.livro = livro; self.janela_principal = janela_principal # MUDANÇA: 'disciplina' -> 'topico'
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.mostrar_menu_contexto)
        self.default_icon_size=QSize(120,170);self.hover_icon_size=QSize(130,185)
        self.setStyleSheet("QPushButton { border: 2px solid transparent; background-color: transparent; border-radius: 5px; }")
        self.setIconSize(self.default_icon_size)
        self.zoom_in_animation=QPropertyAnimation(self,b"iconSize");self.zoom_in_animation.setDuration(150);self.zoom_in_animation.setStartValue(self.default_icon_size);self.zoom_in_animation.setEndValue(self.hover_icon_size);self.zoom_in_animation.setEasingCurve(QEasingCurve.OutQuad)
        self.zoom_out_animation=QPropertyAnimation(self,b"iconSize");self.zoom_out_animation.setDuration(150);self.zoom_out_animation.setStartValue(self.hover_icon_size);self.zoom_out_animation.setEndValue(self.default_icon_size);self.zoom_out_animation.setEasingCurve(QEasingCurve.OutQuad)
    def enterEvent(self,e):
        if self.zoom_out_animation.state()==QAbstractAnimation.State.Running:self.zoom_out_animation.stop()
        self.zoom_in_animation.start();super().enterEvent(e)
    def leaveEvent(self,e):
        if self.zoom_in_animation.state()==QAbstractAnimation.State.Running:self.zoom_in_animation.stop()
        self.zoom_out_animation.start();super().leaveEvent(e)
    def mostrar_menu_contexto(self,pos):menu=QMenu();a_e=QAction("Editar Livro",self);a_e.triggered.connect(self.editar);menu.addAction(a_e);a_r=QAction("Remover Livro",self);a_r.triggered.connect(self.remover);menu.addAction(a_r);menu.addSeparator();s_s=QMenu("Marcar como...",self);a_l=QAction("Em Leitura",self);a_l.triggered.connect(lambda:self.definir_status("lendo"));s_s.addAction(a_l);a_c=QAction("Concluído",self);a_c.triggered.connect(lambda:self.definir_status("concluido"));s_s.addAction(a_c);a_nl=QAction("Não Lido",self);a_nl.triggered.connect(lambda:self.definir_status("nao_lido"));s_s.addAction(a_nl);menu.addMenu(s_s);menu.exec(self.mapToGlobal(pos))
    def editar(self):
        dialog_titulo=QInputDialog(self);dialog_titulo.setWindowTitle("Editar Título");dialog_titulo.setLabelText("Novo título:");dialog_titulo.setTextValue(self.livro['titulo']);dialog_titulo.resize(500,100);ok1=dialog_titulo.exec();novo_titulo=dialog_titulo.textValue()
        if ok1 and novo_titulo:
            nova_pagina,ok2=QInputDialog.getInt(self,"Editar Página","Página atual:",value=self.livro['pagina_atual'],min=1)
            if ok2:self.livro['titulo']=novo_titulo;self.livro['pagina_atual']=nova_pagina;self.janela_principal.salvar_e_recarregar()
    def remover(self):
        if QMessageBox.question(self,"Confirmar Remoção",f"Tem certeza que deseja remover o livro '{self.livro['titulo']}'?",QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No)==QMessageBox.StandardButton.Yes:self.topico['livros'].remove(self.livro);self.janela_principal.salvar_e_recarregar() # MUDANÇA: 'disciplina' -> 'topico'
    def definir_status(self,s):self.livro['status']=s;self.janela_principal.salvar_e_recarregar()

class ScrollAreaArrastavel(QScrollArea):
    def __init__(self,*a,**k):super().__init__(*a,**k);self.setWidgetResizable(True);self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff);self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff);self.is_dragging=False;self.last_mouse_pos=QPoint();self.drag_start_pos=QPoint();self.setCursor(QCursor(Qt.CursorShape.OpenHandCursor));self.gradient_overlay=QWidget(self);self.gradient_overlay.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents);self.update_gradient_stylesheet()
    def update_gradient_stylesheet(self):bg=self.palette().color(QPalette.ColorRole.Window);ct=f"rgba({bg.red()},{bg.green()},{bg.blue()},0)";cs=f"rgba({bg.red()},{bg.green()},{bg.blue()},255)";s=f"""QWidget{{background-color:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 {ct},stop:1 {cs});}}""";self.gradient_overlay.setStyleSheet(s)
    def resizeEvent(self,e):super().resizeEvent(e);bh=200;gw=50;y=(self.height()-bh)/2.0;self.gradient_overlay.setGeometry(self.width()-gw,int(y),gw,bh);self.gradient_overlay.raise_()
    def eventFilter(self,w,e):
        if isinstance(w,QPushButton):
            if e.type()==QEvent.Type.MouseButtonPress:self.mousePressEvent(e);return True
            if e.type()==QEvent.Type.MouseMove:self.mouseMoveEvent(e);return True
            if e.type()==QEvent.Type.MouseButtonRelease:self.mouseReleaseEvent(e,clicked_widget=w);return True
        return super().eventFilter(w,e)
    def mousePressEvent(self,e):
        if e.button()==Qt.MouseButton.LeftButton:self.is_dragging=True;self.drag_start_pos=e.globalPosition().toPoint();self.last_mouse_pos=e.globalPosition().toPoint();self.setCursor(QCursor(Qt.CursorShape.ClosedHandCursor))
        super().mousePressEvent(e)
    def mouseMoveEvent(self,e):
        if self.is_dragging:cp=e.globalPosition().toPoint();d=cp-self.last_mouse_pos;self.last_mouse_pos=cp;hb=self.horizontalScrollBar();hb.setValue(hb.value()-d.x())
        super().mouseMoveEvent(e)
    def mouseReleaseEvent(self,e,cw=None):
        if e.button()==Qt.MouseButton.LeftButton and self.is_dragging:self.is_dragging=False;self.setCursor(QCursor(Qt.CursorShape.OpenHandCursor));rp=e.globalPosition().toPoint();dist=(rp-self.drag_start_pos).manhattanLength();(lambda:cw.click())() if cw and dist<QApplication.styleHints().startDragDistance() else None
        super().mouseReleaseEvent(e)

# --- CLASSE DA INTERFACE PRINCIPAL ---

class JanelaPrincipal(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Gerenciador de Estudos') # Removido (dialog) para um nome mais limpo
        self.resize(400,900)
        self.main_layout=QVBoxLayout(self)
        
        # MUDANÇA: Renomeação
        btn_novo_topico=QPushButton("＋ Adicionar Novo Tópico")
        btn_novo_topico.clicked.connect(self.adicionar_topico)
        self.main_layout.addWidget(btn_novo_topico)
        
        self.scroll_area_main=QScrollArea();self.scroll_area_main.setWidgetResizable(True);self.scroll_area_main.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.content_layout=None;self.main_layout.addWidget(self.scroll_area_main)

        ### MUDANÇA: Barra de Status ###
        self.status_bar = QLabel("Carregando...")
        self.status_bar.setStyleSheet("padding: 2px 5px; color: grey;")
        self.main_layout.addWidget(self.status_bar)

        self.carregar_dados()

    def carregar_dados(self):
        try:
            with open('data.json','r',encoding='utf-8') as f:self.dados=json.load(f)
        except(FileNotFoundError,json.JSONDecodeError):self.dados={"topicos":[]} # MUDANÇA: 'disciplinas' -> 'topicos'
        self.exibir_conteudo()

    def salvar_e_recarregar(self):
        with open('data.json','w',encoding='utf-8') as f:json.dump(self.dados,f,indent=2,ensure_ascii=False)
        self.exibir_conteudo()

    def exibir_conteudo(self):
        ow=self.scroll_area_main.takeWidget();(lambda:ow.deleteLater())() if ow is not None else None;
        
        ### MUDANÇA: Tela Inicial (Empty State) ###
        if not self.dados.get("topicos"):
            # Se não há tópicos, mostra a tela inicial
            container_vazio = QWidget()
            layout_vazio = QVBoxLayout(container_vazio)
            layout_vazio.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            seta = QLabel("︿")
            seta.setStyleSheet("font-size: 50pt; color: #ccc;") # Cor cinza claro
            
            texto = QLabel("Clique em 'Adicionar Novo Tópico' para começar")
            texto.setStyleSheet("font-size: 11pt; color: grey;")

            layout_vazio.addStretch()
            layout_vazio.addWidget(seta)
            layout_vazio.addWidget(texto)
            layout_vazio.addStretch()
            
            self.scroll_area_main.setWidget(container_vazio)
        else:
            # Se há tópicos, mostra a lista normal
            container_widget=QWidget();self.content_layout=QVBoxLayout(container_widget);self.content_layout.setContentsMargins(10,10,10,10);self.content_layout.setSpacing(15);self.scroll_area_main.setWidget(container_widget)
            for topico in self.dados['topicos']: # MUDANÇA: 'disciplina' -> 'topico'
                hl=QHBoxLayout();l=QLabel(f"<b>{topico['nome']}</b>");l.setStyleSheet("font-size: 14pt;");be=QPushButton("Editar");be.setFixedSize(60,25);be.clicked.connect(lambda c,t=topico:self.editar_topico(t));br=QPushButton("Remover");br.setFixedSize(70,25);br.clicked.connect(lambda c,t=topico:self.remover_topico(t));hl.addWidget(l);hl.addStretch();hl.addWidget(be);hl.addWidget(br);self.content_layout.addLayout(hl)
                sa=ScrollAreaArrastavel();sa.setFixedHeight(250);sa.setStyleSheet("QScrollArea { border: none; }");lc=QWidget();ll=QHBoxLayout(lc)
                for livro in topico['livros']:
                    lwc=QWidget();lwc.setFixedWidth(140);lvl=QVBoxLayout(lwc);lvl.setContentsMargins(0,0,0,0);lvl.setSpacing(4)
                    bl=BotaoLivro(topico,livro,self);bl.setFixedSize(140,200);ct=gerar_thumbnail(livro['caminho_pdf'],'thumbnails');(lambda:bl.setIcon(QIcon(ct)))() if ct else None;bl.setToolTip(f"{livro['titulo']}\nPágina: {livro['pagina_atual']}");bl.clicked.connect(lambda c,p=livro['caminho_pdf']:abrir_pdf_compativel(p));bl.installEventFilter(sa)
                    sa_c=livro.get('status','nao_lido');cfg=STATUS_CONFIG[sa_c];ls=QLabel(f"<b>{cfg['texto']}</b>");ls.setAlignment(Qt.AlignmentFlag.AlignCenter);ls.setStyleSheet(f"color: {cfg['cor']}; font-size: 10pt;")
                    lvl.addWidget(bl);lvl.addWidget(ls);ll.addWidget(lwc)
                abc=QWidget();abc.setFixedWidth(140);abl=QVBoxLayout(abc);abl.setContentsMargins(0,0,0,0);abl.setSpacing(4);bal=QPushButton("+");bal.setFixedSize(140,200);bal.setStyleSheet("font-size: 48pt; color: grey; border-radius: 5px;");bal.clicked.connect(lambda c,t=topico:self.adicionar_livro(t));el=QLabel("");abl.addWidget(bal);abl.addWidget(el);ll.addWidget(abc)
                sa.setWidget(lc);self.content_layout.addWidget(sa)
            self.content_layout.addStretch()

        self.atualizar_status_bar()

    def atualizar_status_bar(self):
        data_modificacao = "Nunca"
        if os.path.exists('data.json'):
            timestamp = os.path.getmtime('data.json')
            data_modificacao = datetime.datetime.fromtimestamp(timestamp).strftime('%d/%m/%Y %H:%M')
        
        self.status_bar.setText(f"Creator: Gustavo Borges  |  Atualizado em: {data_modificacao}")

    def _get_text_from_dialog(self, title, label, initial_text=""):
        dialog = QInputDialog(self);dialog.setWindowTitle(title);dialog.setLabelText(label);dialog.setTextValue(initial_text);dialog.resize(500,100);ok = dialog.exec();text = dialog.textValue();return text, ok

    def adicionar_topico(self):
        nome_topico, ok = self._get_text_from_dialog("Novo Tópico", "Nome do Tópico:")
        if ok and nome_topico:
            if "topicos" not in self.dados: self.dados["topicos"] = []
            self.dados['topicos'].append({"nome": nome_topico, "livros": []})
            self.salvar_e_recarregar()

    def editar_topico(self, topico):
        novo_nome, ok = self._get_text_from_dialog("Editar Tópico", "Novo nome:", initial_text=topico['nome'])
        if ok and novo_nome:
            topico['nome'] = novo_nome
            self.salvar_e_recarregar()
            
    def remover_topico(self, topico):
        if QMessageBox.question(self,"Confirmar Remoção",f"Tem certeza que deseja remover o tópico '{topico['nome']}' e todos os seus livros?",QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No)==QMessageBox.StandardButton.Yes:
            self.dados['topicos'].remove(topico)
            self.salvar_e_recarregar()

    def adicionar_livro(self, topico):
        caminho_pdf, _ = QFileDialog.getOpenFileName(self, "Selecionar PDF", "", "Arquivos PDF (*.pdf)")
        if caminho_pdf:
            nome_sugerido = os.path.basename(caminho_pdf).replace('.pdf', '')
            titulo, ok1 = self._get_text_from_dialog("Título do Livro", "Título:", initial_text=nome_sugerido)
            if ok1 and titulo:
                pagina, ok2 = QInputDialog.getInt(self, "Página Atual", "Página inicial:", value=1, min=1)
                if ok2:
                    novo_livro = {"titulo": titulo, "caminho_pdf": caminho_pdf, "pagina_atual": pagina, "status": "nao_lido"}
                    topico['livros'].append(novo_livro)
                    self.salvar_e_recarregar()

# --- PONTO DE ENTRADA DO PROGRAMA ---
if __name__ == "__main__":
    caminho_do_seu_pdf = "exemplo.pdf" # Usar um nome genérico
    # Para o primeiro uso, vamos criar um PDF vazio se ele não existir
    if not os.path.exists(caminho_do_seu_pdf):
        # Esta parte requer a biblioteca 'reportlab'
        try:
            from reportlab.pdfgen import canvas
            from reportlab.lib.pagesizes import letter
            c = canvas.Canvas(caminho_do_seu_pdf, pagesize=letter)
            c.drawString(100, 750, "Este é um PDF de exemplo gerado automaticamente.")
            c.save()
        except ImportError:
            print("AVISO: 'reportlab' não instalado. Não foi possível gerar o PDF de exemplo.")
            print("Por favor, crie um arquivo 'exemplo.pdf' manualmente ou instale a biblioteca: pip install reportlab")

    gerar_dados_simulados('data.json', caminho_do_seu_pdf)
    app = QApplication(sys.argv)
    QApplication.setEffectEnabled(Qt.UIEffect.UI_AnimateTooltip, False)
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    janela = JanelaPrincipal()
    janela.show()
    sys.exit(app.exec())