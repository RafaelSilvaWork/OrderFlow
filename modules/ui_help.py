"""Janela de Ajuda: guia de uso por módulo + solução de problemas comuns.

Conteúdo estático (HTML renderizado num QTextBrowser) - não depende de
nenhum outro módulo do framework. Aberta como diálogo (HelpDialog), tanto
pelo botão "❓ Ajuda" no header quanto pelo botão de ajuda contextual de
cada aba de módulo (HelpCornerButton) - não é mais uma aba fixa na barra de
módulos.
"""

from PyQt6.QtCore import QEvent, Qt
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSplitter,
    QTabWidget,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from modules.branding import APP_DATA_DIR_NAME, APP_DISPLAY_NAME
from modules.styles import aplicar_titlebar_escura

_CSS = """
body { color: #e6edf3; font-family: 'Segoe UI', sans-serif; font-size: 14px; }
h2 { color: #58a6ff; border-bottom: 1px solid #30363d; padding-bottom: 6px; margin-top: 4px; }
h3 { color: #22d3ee; margin-top: 18px; }
p { color: #e6edf3; line-height: 1.5; }
li { margin-bottom: 6px; line-height: 1.4; }
b, strong { color: #e6edf3; }
code { background-color: #161b22; color: #d29922; padding: 1px 5px; border-radius: 3px; }
.dica { background-color: #161b22; border-left: 3px solid #58a6ff; padding: 8px 14px; margin: 10px 0; }
.erro { background-color: #161b22; border-left: 3px solid #f85149; padding: 8px 14px; margin: 10px 0; }
.msg { color: #f85149; }
"""

_VISAO_GERAL = """
<h2>🏠 Visão Geral</h2>
<p>O CoupaFramework automatiza o fluxo de compras no Coupa em 7 etapas, cada uma numa aba. O fluxo típico é:</p>
<ol>
<li><b>📦 Extrator Inteligente</b> - lê requisições no Coupa e descobre os pedidos (PO) gerados.</li>
<li><b>📥 Baixador de Orçamentos</b> - baixa os anexos de orçamento de cada requisição.</li>
<li><b>📄 Gerador de PDF de Pedidos</b> - gera um PDF de cada pedido (PO).</li>
<li><b>📝 Renomeador</b> - renomeia PDFs de pedidos com base no conteúdo deles.</li>
<li><b>🗂️ Organizador</b> - organiza propostas/pedidos em pastas por fornecedor.</li>
<li><b>📧 Disparo de E-mails</b> - envia e-mail de autorização por fornecedor.</li>
</ol>
<p>A aba <b>👥 Gerenciar Perfis</b> não faz parte do fluxo - é onde você configura a instância do Coupa,
perfis de extração, template de e-mail e as planilhas de mapeamento (fornecedores/unidades/solicitantes)
usadas pelas outras abas.</p>
<div class="dica">
<b>Fluxo Automático:</b> na aba Extrator, marque quais abas seguintes devem rodar sozinhas depois da
extração (checkboxes "Aba 2", "Aba 3" etc). O app confere se cada uma está configurada corretamente
<i>antes</i> de começar - se faltar algo, mostra exatamente o que ajustar.
</div>
<p>Use a lista à esquerda para ver o guia de cada aba, ou a seção <b>🛠️ Solução de Problemas</b> para
mensagens de erro comuns.</p>
"""

_EXTRATOR = """
<h2>📦 Extrator Inteligente</h2>
<p>Lê requisições do Coupa e descobre qual pedido (PO) foi gerado para cada uma, junto com dados como
fornecedor, quem criou/solicitou e e-mails encontrados na justificativa.</p>
<h3>Como usar</h3>
<ol>
<li>Escolha um <b>perfil</b> no menu (crie um antes em "Gerenciar Perfis" se ainda não tiver).</li>
<li>Cole os números das requisições na caixa de texto, um por linha.</li>
<li>Se quiser, marque as abas seguintes que devem rodar automaticamente depois (Fluxo Automático).</li>
<li>Clique em <b>"1. Abrir Edge para Login"</b> - uma janela do Edge abre isolada; faça login manual
no Coupa nela.</li>
<li>Clique em <b>"2. Confirmar Login e Iniciar Extração"</b> para começar de fato.</li>
<li>Acompanhe o progresso na tabela; use Pausar/Retomar/Cancelar se precisar.</li>
<li>Ao final, exporte os resultados para Excel se quiser um arquivo separado.</li>
</ol>
<h3>Pré-requisitos</h3>
<ul>
<li>Um perfil configurado em "Gerenciar Perfis" (controla quais campos são extraídos).</li>
<li>Microsoft Edge instalado no caminho padrão.</li>
<li>Instância do Coupa configurada em "Gerenciar Perfis" → "Instância do Coupa".</li>
</ul>
<div class="dica">Se marcar abas do Fluxo Automático, configure-as (pastas, planilhas, SMTP etc.)
<i>antes</i> de rodar o Extrator - o app avisa o que falta, mas não configura sozinho.</div>
"""

_DOWNLOADER = """
<h2>📥 Baixador de Orçamentos</h2>
<p>Baixa os anexos de orçamento ("de acordo com...", propostas, cotações) de cada requisição no Coupa,
lê o conteúdo de cada arquivo (PDF/DOCX/XLSX/PPTX/CSV/TXT) e só mantém os que realmente parecem ser
um orçamento, descartando anexos que não batem com as palavras-chave esperadas.</p>
<h3>Como usar</h3>
<ol>
<li>Selecione a <b>pasta de destino</b> onde os orçamentos serão salvos.</li>
<li>As requisições vêm automaticamente da aba Extrator (Aba 1); também dá para digitar manualmente.</li>
<li>Clique em <b>"Iniciar Downloads"</b> e acompanhe o progresso (geral + por anexo).</li>
</ol>
<h3>Pré-requisitos</h3>
<ul>
<li>Pasta de destino selecionada.</li>
<li>Requisições disponíveis (rodou a aba Extrator antes, ou digitou manualmente).</li>
<li>Para orçamentos em PDF escaneado (imagem, sem texto selecionável): o app usa OCR (Tesseract) para
ler o conteúdo - já vem empacotado no instalador; só falta em ambiente de desenvolvimento
(<code>python main.py</code> direto do código-fonte).</li>
</ul>
<div class="dica">Um anexo "não reconhecido como orçamento" não é necessariamente um erro - pode ser
um arquivo cujo nome ou conteúdo não bate com as palavras-chave esperadas (orçamento, proposta,
cotação, quotation, budget). O resumo final lista as requisições sem nenhum arquivo válido.</div>
"""

_PDF = """
<h2>📄 Gerador de PDF de Pedidos</h2>
<p>Abre a página de impressão de cada pedido (PO) no Coupa e gera um PDF a partir dela.</p>
<h3>Como usar</h3>
<ol>
<li>Selecione a <b>pasta de destino</b> dos PDFs.</li>
<li>Os números de pedido vêm automaticamente da aba Extrator (Aba 1), ou digite manualmente.</li>
<li>Clique em <b>"Iniciar Geração de PDFs"</b>.</li>
<li>Se o Edge ainda não estiver logado no Coupa, o app espera até 5 minutos para você fazer login
manualmente na janela que abre.</li>
</ol>
<p>Ao final, um relatório em Excel (<code>Relatorio_Geracao_PDF_AAAAMMDD_HHMMSS.xlsx</code>) é sempre
gerado na pasta de destino, com o status de cada pedido (Sucesso, Sem Doc, Erro).</p>
<h3>Pré-requisitos</h3>
<ul>
<li>Pasta de destino selecionada.</li>
<li>Pedidos disponíveis (vindos da aba Extrator, ou digitados manualmente).</li>
<li>Microsoft Edge instalado; instância do Coupa configurada em "Gerenciar Perfis".</li>
</ul>
<div class="dica">Um pedido "Sem Doc" geralmente significa que o Coupa ainda está processando o
documento internamente - o app já tenta recarregar 3 vezes antes de desistir. Rodar de novo mais
tarde costuma resolver.</div>
"""

_RENOMEADOR = """
<h2>📝 Renomeador</h2>
<p>Renomeia PDFs de pedidos já salvos localmente, lendo o conteúdo de cada arquivo para montar o novo
nome no formato <code>PO {id} - {fornecedor} - {unidade}.pdf</code>.</p>
<h3>Como usar</h3>
<ol>
<li>Selecione a pasta com os PDFs.</li>
<li>Clique em <b>"Analisar"</b> - o app lê cada PDF e mostra na tabela se está "✅ Pronto" ou com erro.</li>
<li>Revise a tabela; PDFs com erro (sem "ID Coupa" ou "Fornecedor" reconhecíveis) não serão renomeados.</li>
<li>Clique em <b>"Renomear"</b> - só os arquivos marcados "✅ Pronto" são processados.</li>
</ol>
<p>Antes de cada renomeação, uma cópia de backup é salva em <code>Backup_Renomeamento</code> dentro da
mesma pasta, e todo processamento fica registrado em <code>historico_renomeador.csv</code>
(em <code>%APPDATA%\\CoupaFramework</code>).</p>
<h3>Pré-requisitos</h3>
<ul>
<li>Pasta selecionada, contendo pelo menos um arquivo <code>.pdf</code>.</li>
<li>Os PDFs precisam ter texto selecionável (não escaneado como imagem) com "ID Coupa" e "Fornecedor"
identificáveis - PDFs sem essas informações no texto ficam marcados como erro.</li>
</ul>
"""

_ORGANIZADOR = """
<h2>🗂️ Organizador</h2>
<p>Copia propostas e/ou pedidos para pastas separadas por fornecedor, usando uma planilha de mapeamento
(RC / PO / Fornecedor) para saber qual arquivo vai para qual pasta.</p>
<h3>Como usar</h3>
<ol>
<li>Selecione a <b>Pasta de Propostas</b> e/ou a <b>Pasta de Pedidos</b> (pelo menos uma é obrigatória).</li>
<li>Selecione a <b>Pasta de Destino</b>, onde as pastas por fornecedor serão criadas.</li>
<li>Selecione a <b>planilha de mapeamento</b> (.xlsx ou .csv) com as colunas RC/PO/Fornecedor.</li>
<li>Se sua planilha usa nomes de coluna diferentes, ajuste-os nos campos de configuração.</li>
<li>Clique em <b>"Iniciar Organização"</b>.</li>
</ol>
<p>Uma pasta é criada para cada fornecedor da planilha, mesmo que nenhum arquivo seja encontrado para
ele. Propostas copiadas são renomeadas para <code>PROPOSTA - {RC} - {PO}.ext</code>; pedidos mantêm o
nome original.</p>
<h3>Pré-requisitos</h3>
<ul>
<li>Pelo menos uma das pastas (Propostas ou Pedidos), a pasta de destino e a planilha, todas
selecionadas e válidas.</li>
<li>A planilha precisa ter, no cabeçalho, as colunas configuradas (padrão: "RC", "PO", "FORNECEDOR").</li>
</ul>
"""

_EMAIL = """
<h2>📧 Disparo de E-mails</h2>
<p>Envia um e-mail de "Autorização PC" por fornecedor, usando os dados vindos das abas anteriores e
os e-mails de destinatário encontrados nas planilhas de mapeamento (Fornecedores, Unidades,
Solicitantes) configuradas em "Gerenciar Perfis".</p>
<h3>Como usar</h3>
<ol>
<li>Garanta que há dados carregados (vindos do Fluxo Automático, ou clique em
"Carregar Planilha de Resultados Manualmente").</li>
<li>Escolha um <b>perfil</b> (controla o template do e-mail e a lista de cópia do comprador).</li>
<li>Escolha o modo de envio: <b>SMTP</b>, <b>Outlook Desktop</b> ou <b>Power Automate</b>.</li>
<li>Preencha as configurações do modo escolhido (host/porta/usuário/senha para SMTP, ou a URL do
flow em "Gerenciar Perfis" para Power Automate).</li>
<li>Clique em <b>"🚀 Enviar E-mails Agora"</b> e confirme no diálogo de prévia.</li>
</ol>
<h3>Pré-requisitos por modo de envio</h3>
<ul>
<li><b>SMTP:</b> host, porta, usuário e senha preenchidos (dá para salvar com segurança usando o
Gerenciador de Credenciais do Windows, via <code>keyring</code>).</li>
<li><b>Outlook Desktop:</b> precisa do pacote <code>pywin32</code> instalado e do Outlook configurado
na máquina.</li>
<li><b>Power Automate:</b> URL do flow configurada em "Gerenciar Perfis".</li>
</ul>
<p>As planilhas de mapeamento (fornecedores/unidades/solicitantes) precisam existir e ter uma coluna
de e-mail - se um mapeamento não for encontrado, o envio não trava, mas aquele destinatário
específico pode não ser incluído.</p>
"""

_PERFIS = """
<h2>👥 Gerenciar Perfis</h2>
<p>É a central de configuração usada pelas outras abas:</p>
<ul>
<li><b>Instância do Coupa</b> - a URL da sua instância (ex: <code>suaempresa.coupahost.com</code>),
usada pelo Extrator, Baixador e Gerador de PDF.</li>
<li><b>URL do Power Automate</b> - usada pela aba de E-mails quando o modo de envio é Power Automate.</li>
<li><b>Perfis</b> - cada perfil controla quais campos o Extrator coleta (Criado Por, Solicitado Por,
E-mails, Destino), o(s) e-mail(s) em cópia do comprador, e o template HTML do e-mail (aceita
<code>{pedido}</code>, <code>{req}</code>, <code>{fornecedor}</code>, <code>{criado_por}</code>,
<code>{solicitado_por}</code>, <code>{localidade}</code>, <code>{comprador}</code>).</li>
<li><b>Planilhas de mapeamento</b> (Fornecedores/Unidades/Solicitantes) - editáveis direto numa
tabela dentro do app, com importação/exportação para Excel.</li>
</ul>
<div class="dica">Tudo que é sensível (senha de e-mail, e-mails do comprador, template, URL do
Power Automate) fica <b>criptografado</b> em disco, amarrado a esta máquina - copiar os arquivos de
configuração para outro computador não funciona; configure de novo lá.</div>
"""

_TROUBLESHOOTING = """
<h2>🛠️ Solução de Problemas</h2>
<p>Mensagens agrupadas por causa provável. Procure pelo texto que apareceu no app.</p>

<h3>Conexão com o Coupa</h3>
<ul>
<li><span class="msg">"Sem conexão com a internet, ou a URL da instância do Coupa está incorreta."</span>
- confira sua rede e a instância configurada em "Gerenciar Perfis".</li>
<li><span class="msg">"Não foi possível conectar à instância do Coupa configurada."</span> - o Coupa
pode estar fora do ar, ou VPN/firewall está bloqueando o acesso.</li>
<li><span class="msg">"O Coupa demorou demais para responder (timeout)."</span> - conexão lenta ou
Coupa sobrecarregado; tente de novo.</li>
</ul>

<h3>Microsoft Edge</h3>
<ul>
<li><span class="msg">"Caminho do Microsoft Edge não encontrado."</span> - instale o Edge no caminho
padrão, ou defina a variável de ambiente <code>EDGE_EXECUTABLE_PATH</code>.</li>
<li><span class="msg">"Feche o Edge e tente novamente."</span> / erro ao anexar ao Edge - o
CoupaFramework usa um perfil próprio do Edge; feche <b>todas</b> as janelas do Edge (inclusive as
abertas por outro perfil) antes de tentar de novo.</li>
</ul>

<h3>OCR / Tesseract (orçamentos em PDF escaneado)</h3>
<ul>
<li><span class="msg">"OCR indisponível: Tesseract não encontrado nesta máquina."</span> - só acontece
rodando o código-fonte diretamente (<code>python main.py</code>); no instalador normal o Tesseract já
vem incluso. Em modo desenvolvimento, instale o Tesseract (com o pacote de idioma Português) e
adicione ao PATH.</li>
</ul>

<h3>Atualização e módulos</h3>
<ul>
<li><span class="msg">"Limite de requisições do GitHub atingido."</span> - comum em redes com IP
compartilhado (vários colegas na mesma rede); espere alguns minutos e tente de novo.</li>
<li><span class="msg">"Verificação de integridade do instalador falhou (checksum não confere)."</span>
- o instalador baixado está corrompido ou foi adulterado; o app se recusa a executá-lo por segurança.
Tente baixar de novo.</li>
<li><b>"Módulo não instalado"</b> - a aba não foi selecionada na instalação; clique em
"Baixar este módulo" na própria aba bloqueada.</li>
<li><b>"Módulo indisponível"</b> - o módulo deveria funcionar mas falhou ao carregar; use
"Reinstalar módulo" para tentar corrigir baixando os arquivos de novo.</li>
</ul>

<h3>Perfis, planilhas e criptografia</h3>
<ul>
<li>Campos de perfil aparecendo como texto estranho/ilegível - geralmente indica que o arquivo de
criptografia local (<code>coupa_fw.secret</code>) foi perdido ou trocado; reconfigure o campo afetado
manualmente.</li>
<li><span class="msg">"Colunas não encontradas no cabeçalho"</span> (Organizador) - o nome das colunas
na sua planilha não bate com o configurado; ajuste os nomes de coluna na aba Organizador ou renomeie
o cabeçalho da planilha.</li>
<li>E-mail de fornecedor/unidade/solicitante não incluído no envio - confira se o nome está cadastrado
(com e-mail preenchido) na planilha de mapeamento correspondente, em "Gerenciar Perfis".</li>
</ul>

<h3>Acesso bloqueado</h3>
<ul>
<li><b>"Acesso bloqueado"</b> ao abrir o app - o acesso deste usuário/máquina foi revogado
remotamente. Entre em contato com o responsável pela distribuição do aplicativo.</li>
</ul>

<div class="dica">Não achou o que procurava? A maioria dos erros específicos de cada aba (não
cobertos aqui) aparece com uma descrição direta na própria tela - releia a mensagem completa, ela
geralmente já diz o que fazer.</div>
"""

_SECOES: list[tuple[str, str, str]] = [
    ("visao_geral", "🏠 Visão Geral", _VISAO_GERAL),
    ("extrator", "📦 Extrator Inteligente", _EXTRATOR),
    ("downloader", "📥 Baixador de Orçamentos", _DOWNLOADER),
    ("pdf", "📄 Gerador de PDF de Pedidos", _PDF),
    ("renomeador", "📝 Renomeador", _RENOMEADOR),
    ("organizador", "🗂️ Organizador", _ORGANIZADOR),
    ("email", "📧 Disparo de E-mails", _EMAIL),
    ("perfis", "👥 Gerenciar Perfis", _PERFIS),
    ("troubleshooting", "🛠️ Solução de Problemas", _TROUBLESHOOTING),
]
# Conteúdo escrito com o nome/pasta fixos do Hapvida (marca padrão) - troca
# pelos valores da marca ativa (ver modules/branding.py) sem precisar
# reescrever cada bloco como f-string (o HTML/CSS já usa muito "{"/"}").
_SECOES = [
    (
        chave,
        titulo,
        html.replace("%APPDATA%\\CoupaFramework", f"%APPDATA%\\{APP_DATA_DIR_NAME}")
        .replace("CoupaFramework", APP_DISPLAY_NAME),
    )
    for chave, titulo, html in _SECOES
]


class HelpWidget(QWidget):
    """Aba de Ajuda: lista de seções à esquerda, conteúdo renderizado à direita."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(12, 12, 12, 12)
        outer_layout.setSpacing(8)

        self.busca = QLineEdit()
        self.busca.setPlaceholderText("🔎 Buscar por palavra-chave (ex: checksum, Edge, e-mail...)")
        self.busca.textChanged.connect(self._filtrar_secoes)
        outer_layout.addWidget(self.busca)

        splitter = QSplitter()

        self.lista = QListWidget()
        self.lista.setMaximumWidth(260)
        for key, titulo, _ in _SECOES:
            item = QListWidgetItem(titulo)
            item.setData(1000, key)
            self.lista.addItem(item)
        self.lista.currentRowChanged.connect(self._on_selecao_mudou)

        self.conteudo = QTextBrowser()
        self.conteudo.setOpenExternalLinks(True)
        self.conteudo.document().setDefaultStyleSheet(_CSS)

        splitter.addWidget(self.lista)
        splitter.addWidget(self.conteudo)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)

        layout = QHBoxLayout()
        layout.addWidget(splitter)
        outer_layout.addLayout(layout)

        self.lista.setCurrentRow(0)

    def selecionar_secao(self, key: str) -> None:
        """Pula direto para uma seção pelo key (ex: "extrator", "perfis").

        Limpa qualquer filtro de busca ativo antes, senão a seção poderia
        estar oculta pelo filtro anterior.
        """
        self.busca.clear()
        for row in range(self.lista.count()):
            if self.lista.item(row).data(1000) == key:
                self.lista.setCurrentRow(row)
                return

    def _on_selecao_mudou(self, row: int):
        if row < 0 or row >= len(_SECOES):
            return
        _, _, html = _SECOES[row]
        self.conteudo.setHtml(html)

    def _filtrar_secoes(self, texto: str):
        termo = texto.strip().lower()
        primeira_visivel = None
        for row, (_, titulo, html) in enumerate(_SECOES):
            visivel = not termo or termo in titulo.lower() or termo in html.lower()
            self.lista.item(row).setHidden(not visivel)
            if visivel and primeira_visivel is None:
                primeira_visivel = row

        item_atual = self.lista.currentItem()
        selecao_ainda_visivel = item_atual is not None and not item_atual.isHidden()
        if not selecao_ainda_visivel and primeira_visivel is not None:
            self.lista.setCurrentRow(primeira_visivel)


class HelpDialog(QDialog):
    """Janela de Ajuda, aberta pelo botão "❓ Ajuda" do header ou pelo botão
    de ajuda contextual de cada aba de módulo (HelpCornerButton).
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Ajuda - {APP_DISPLAY_NAME}")
        aplicar_titlebar_escura(self)
        self.resize(900, 600)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.help_widget = HelpWidget(self)
        layout.addWidget(self.help_widget)

    def selecionar_secao(self, key: str) -> None:
        self.help_widget.selecionar_secao(key)


class HelpCornerButton(QPushButton):
    """Botão de ajuda contextual ancorado na borda entre a barra de abas e o conteúdo.

    Não usa QTabWidget.setCornerWidget: essa área fica dentro da própria
    barra de abas e passou a competir por espaço com as setas de rolagem
    quando há muitas abas (ficava espremido/cortado). Em vez disso, o botão
    é um filho direto do QTabWidget, posicionado "à mão" no canto direito,
    logo abaixo da linha divisória entre a barra de abas e o conteúdo - não
    faz parte de nenhuma das duas áreas, então nunca disputa espaço com as
    abas nem sobrepõe painéis internos de um módulo.
    """

    _TAMANHO = 26
    _MARGEM_DIREITA = 12
    _DESLOCAMENTO_VERTICAL = 12.5  # empurra o botão pra baixo da linha divisória

    def __init__(self, tab_widget: QTabWidget, ao_clicar):
        super().__init__("❓", tab_widget)
        self.setObjectName("helpOverlayButton")
        self.setFixedSize(self._TAMANHO, self._TAMANHO)
        self.setToolTip("Ajuda sobre esta aba")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clicked.connect(ao_clicar)
        self._tab_widget = tab_widget
        tab_widget.installEventFilter(self)
        self._reposicionar()
        self.raise_()
        self.show()

    def eventFilter(self, obj, event):
        if obj is self._tab_widget and event.type() in (
            QEvent.Type.Resize,
            QEvent.Type.LayoutRequest,
            QEvent.Type.Show,
        ):
            self._reposicionar()
        return False

    def _reposicionar(self):
        altura_barra_abas = self._tab_widget.tabBar().height()
        x = self._tab_widget.width() - self._TAMANHO - self._MARGEM_DIREITA
        y = round(altura_barra_abas - self._TAMANHO / 2 + self._DESLOCAMENTO_VERTICAL)
        self.move(x, y)
        self.raise_()
