# ==================================================================
#   FICHEIRO: app.py (VERSÃO ATUALIZADA PARA POSTGRESQL)
# ==================================================================
import os
import json
from datetime import datetime
from functools import wraps

# --- Importações de bibliotecas externas ---
import requests
from flask import (Flask, render_template, request, redirect, url_for, 
                   session, flash, jsonify, abort, make_response)
from werkzeug.utils import secure_filename
# --- NOVAS IMPORTAÇÕES PARA POSTGRESQL ---
from flask_sqlalchemy import SQLAlchemy

# Adicionada a importação que estava faltando para gerar PDF
try:
    from weasyprint import HTML
except ImportError:
    HTML = None
    print("AVISO: WeasyPrint não está instalado. A geração de PDF não funcionará.")

# ==================================================================
# 1. CONFIGURAÇÃO INICIAL DA APLICAÇÃO E BANCO DE DADOS
# ==================================================================
app = Flask(__name__, template_folder="templates")

# --- CONFIGURAÇÃO DE DADOS SENSÍVEIS ---
# Pega a Secret Key e a URL do Banco de Dados das variáveis de ambiente do Render
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'chave_padrao_para_desenvolvimento_local')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///local_vigilancia.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# --- INICIALIZAÇÃO DO BANCO DE DADOS ---
db = SQLAlchemy(app)

# Garante que a pasta de uploads exista
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)


# ==================================================================
# 2. MODELO DO BANCO DE DADOS (TABELA DE SOLICITAÇÕES)
# ==================================================================
class Solicitacoes(db.Model):
    """Define a estrutura da tabela 'solicitacoes'."""
    id = db.Column(db.Integer, primary_key=True)
    protocolo = db.Column(db.String(80), unique=True, nullable=False)
    tipo_solicitacao = db.Column(db.String(120), nullable=False)
    dados_formulario = db.Column(db.Text, nullable=False) # Armazena o JSON como texto
    status = db.Column(db.String(50), default='Em análise')
    justificativa_status = db.Column(db.Text, nullable=True)
    data_solicitacao = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Solicitacao {self.protocolo}>'


# ==================================================================
# 3. FUNÇÕES AUXILIARES E FILTROS DE TEMPLATE
# ==================================================================
def gerar_protocolo():
    """Gera um protocolo único baseado na data/hora."""
    return f"VISA-{datetime.now().strftime('%Y%m%d%H%M%S')}"

# ... (outros filtros e decoradores permanecem os mesmos) ...
@app.template_filter('datetimeformat')
def datetimeformat(value, format='%d/%m/%Y'):
    if isinstance(value, datetime):
        return value.strftime(format)
    try:
        return datetime.strptime(str(value).split(" ")[0], '%Y-%m-%d').strftime(format)
    except (ValueError, TypeError):
        return value

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            flash('É necessário fazer login para acessar esta página.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# ==================================================================
# 4. ROTA UNIFICADA PARA SUBMISSÃO DE FORMULÁRIOS
# ==================================================================
@app.route('/submeter_solicitacao', methods=['POST'])
def submeter_solicitacao():
    protocolo = gerar_protocolo()
    tipo_solicitacao = request.form.get('tipo_solicitacao', 'Desconhecido')
    
    dados_dict = dict(request.form)
    if 'cnpj' in dados_dict:
        dados_dict['cnpj_limpo'] = ''.join(filter(str.isdigit, dados_dict.get('cnpj', '')))
    dados_dict.pop('tipo_solicitacao', None)
    dados_json = json.dumps(dados_dict, indent=4, ensure_ascii=False)

    # Nova lógica com SQLAlchemy
    nova_solicitacao = Solicitacoes(
        protocolo=protocolo,
        tipo_solicitacao=tipo_solicitacao,
        dados_formulario=dados_json
    )
    db.session.add(nova_solicitacao)
    db.session.commit()

    flash(f'Sua solicitação de "{tipo_solicitacao}" foi enviada com sucesso! Anote seu protocolo: {protocolo}', 'success')
    return redirect(url_for('index'))

# ==================================================================
# 5. ROTAS PÚBLICAS (Páginas de Formulários e Consultas)
# ==================================================================
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/abertura-empresa')
def abertura_empresa():
    return render_template('form_nova_empresa.html')

@app.route('/solicitacao-receituarios')
def solicitacao_receituarios():
    return render_template('form_solicitacao_receituarios.html')

@app.route('/requerimento-inicial')
def requerimento_inicial():
    return render_template('requerimento_inicial.html')

@app.route('/alteracao-empresa')
def alteracao_empresa():
    return render_template('form_alteracao.html')

@app.route('/anuidade')
def anuidade():
    return render_template('form_anuidade.html')

@app.route('/dispensa-licenca')
def dispensa_licenca():
    return render_template('form_dispensa_licenca.html')

@app.route('/licenca-evento')
def licenca_evento():
    return render_template('form_licenca_evento.html')

@app.route('/denuncia')
def denuncia():
    return render_template('form_denuncia.html')

@app.route('/licenca-instituicao-publica')
def licenca_instituicao_publica():
    return render_template('form_licenca_instituicao.html')

@app.route('/vistorias-denuncias')
def vistorias_denuncias():
    return render_template('vistorias_denuncias_menu.html')

@app.route('/registrar-denuncia')
def registrar_denuncia():
    return render_template('form_denuncia.html')

@app.route('/registrar-vistoria')
def registrar_vistoria():
    return render_template('form_vistoria.html')

@app.route('/atendimento-denuncia')
def atendimento_denuncia():
    return render_template('form_atendimento_denuncia.html')

# ROTA ADICIONADA PARA GERAR NOTIFICAÇÃO
@app.route('/gerar-notificacao')
def gerar_notificacao():
    return render_template('form_notificacao.html')

@app.route('/teste-calazar')
def teste_calazar():
    return render_template('form_teste_calazar.html')

@app.route('/cancelamento')
def cancelamento():
    return render_template('form_cancelamento.html')

# --- Rota de Consulta Unificada ---
@app.route('/consulta-unificada', methods=['GET', 'POST'])
def consulta_unificada():
    solicitacao = None
    if request.method == 'POST':
        protocolo = request.form.get('protocolo', '').strip()
        if protocolo:
            # Nova lógica com SQLAlchemy
            solicitacao = Solicitacoes.query.filter_by(protocolo=protocolo).first()
            if not solicitacao:
                flash('Protocolo não encontrado. Verifique o número e tente novamente.', 'warning')
    return render_template('consulta_unificada.html', solicitacao=solicitacao)

# ROTA ADICIONADA PARA GERAR AUTO DE INFRAÇÃO
@app.route('/gerar-auto-infracao')
def gerar_auto_infracao():
    return render_template('form_auto_infracao.html')


# ==================================================================
# 6. ROTAS DE AUTENTICAÇÃO E ÁREA ADMINISTRATIVA
# ==================================================================
users_db = {"admin": {"password": "admin123", "nome": "Administrador"}} # Manter por enquanto

@app.route('/login', methods=['GET', 'POST'])
def login():
    # ... (lógica de login não muda) ...
    if 'logged_in' in session:
        return redirect(url_for('admin_index'))
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = users_db.get(username)
        if user and user['password'] == password:
            session['logged_in'] = True
            session['user_id'] = username
            return redirect(url_for('admin_index'))
        else:
            flash('Usuário ou senha inválidos.', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Logout efetuado com sucesso.', 'info')
    return redirect(url_for('index'))

@app.route('/admin/dashboard')
@login_required
def admin_index():
    return render_template('admin_index.html')

@app.route('/admin/empresas')
@login_required
def admin_empresas_lista():
    # No futuro, esta página pode ter uma lógica mais complexa.
    # Por enquanto, vamos redirecionar para a lista de todas as solicitações.
    return redirect(url_for('admin_solicitacoes'))

# ROTA ADICIONADA PARA RELATÓRIOS
@app.route('/admin/relatorios')
@login_required
def admin_relatorios():
    # No futuro, esta rota buscará dados reais do banco.
    # Por enquanto, é apenas um placeholder.
    return render_template('admin_relatorios.html')

@app.route('/admin/solicitacoes')
@login_required
def admin_solicitacoes():
    # Nova lógica com SQLAlchemy
    lista_solicitacoes = Solicitacoes.query.order_by(Solicitacoes.data_solicitacao.desc()).all()
    return render_template('admin_solicitacoes.html', solicitacoes=lista_solicitacoes)

# ROTA ADICIONADA PARA O CNAE
@app.route('/admin/cnae')
@login_required
def admin_cnae_lista():
    # Placeholder para a página de gerenciamento de CNAEs
    return render_template('admin_cnae.html')

@app.route('/admin/avaliar/<int:id>', methods=['GET', 'POST'])
@login_required
def admin_avaliar_solicitacao(id):
    # Nova lógica com SQLAlchemy
    solicitacao_a_avaliar = Solicitacoes.query.get_or_404(id)
    
    if request.method == 'POST':
        solicitacao_a_avaliar.status = request.form.get('status')
        solicitacao_a_avaliar.justificativa_status = request.form.get('justificativa_status', '')
        db.session.commit()
        flash(f"A solicitação foi atualizada para '{solicitacao_a_avaliar.status}'.", 'success')
        return redirect(url_for('admin_solicitacoes'))
    
    dados_formulario = json.loads(solicitacao_a_avaliar.dados_formulario)
    return render_template('admin_avaliacao.html', solicitacao=solicitacao_a_avaliar, dados=dados_formulario)
    

# ==================================================================
# 8. PONTO DE ENTRADA PARA PRODUÇÃO (GUNICORN) E DESENVOLVIMENTO
# ==================================================================
def setup_database():
    """Cria as tabelas do banco de dados se elas não existirem."""
    print("Verificando e criando tabelas do banco de dados...")
    db.create_all()
    print("Tabelas prontas.")

def create_app():
    """Função 'Factory' que o Gunicorn usa para obter a aplicação."""
    print("create_app() chamada pelo servidor de produção (Gunicorn).")
    with app.app_context():
        setup_database()
    return app

if __name__ == '__main__':
    """Bloco para DESENVOLVIMENTO LOCAL."""
    print(">>> EXECUTANDO EM MODO DE DESENVOLVIMENTO LOCAL <<<")
    with app.app_context():
        setup_database()
    app.run(debug=True, host="0.0.0.0", port=5001)
