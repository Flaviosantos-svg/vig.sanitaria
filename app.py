# ==================================================================
#   FICHEIRO: app.py (VERSÃO FINAL, CORRIGIDA E ORGANIZADA)
# ==================================================================
import os
import sqlite3
import json
from datetime import datetime
from functools import wraps

# --- Importações de bibliotecas externas ---
import requests
from flask import (Flask, render_template, request, redirect, url_for, 
                   session, flash, jsonify, abort, make_response)
from werkzeug.utils import secure_filename
# Adicionada a importação que estava faltando para gerar PDF
try:
    from weasyprint import HTML
except ImportError:
    HTML = None
    print("AVISO: WeasyPrint não está instalado. A geração de PDF não funcionará.")
    print("Instale com: pip install WeasyPrint")


# ==================================================================
# 1. CONFIGURAÇÃO INICIAL DA APLICAÇÃO FLASK
# ==================================================================
app = Flask(__name__, template_folder="templates")
app.secret_key = os.environ.get('SECRET_KEY', 'sua_chave_secreta_super_dificil_padrao')
app.config['UPLOAD_FOLDER'] = 'uploads'

# Garante que a pasta de uploads exista
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)



# ==================================================================
# 2. CONFIGURAÇÃO E MANIPULAÇÃO DO BANCO DE DADOS (SQLite)
# ==================================================================
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)

# TADA E TEMPO
@app.template_filter('datetimeformat')
def datetimeformat(value, format='%d/%m/%Y'):
    if isinstance(value, datetime):
        return value.strftime(format)
    try:
        return datetime.strptime(value, '%Y-%m-%d').strftime(format)
    except:
        return value

# --- 2. BANCO DE DADOS ---

def get_db_connection():
    """Cria e retorna uma conexão com o banco de dados."""
    conn = sqlite3.connect('vigilancia.db')
    conn.row_factory = sqlite3.Row
    return conn

def setup_database():
    """Cria TODAS as tabelas do banco de dados se elas não existirem."""
    conn = get_db_connection()
    print("Configurando o banco de dados...")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS solicitacoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            protocolo TEXT NOT NULL UNIQUE,
            tipo_solicitacao TEXT NOT NULL,
            dados_formulario TEXT NOT NULL,
            status TEXT DEFAULT 'Em análise',
            justificativa_status TEXT,
            data_solicitacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    # Adicione aqui a criação de outras tabelas se necessário
    conn.commit()
    conn.close()
    print("Banco de dados configurado com sucesso.")


# ==================================================================
# 3. FUNÇÕES AUXILIARES E FILTROS DE TEMPLATE
# ==================================================================
def gerar_protocolo():
    """Gera um protocolo único baseado na data/hora."""
    return f"VISA-{datetime.now().strftime('%Y%m%d%H%M%S')}"

@app.template_filter('datetimeformat')
def datetimeformat(value, format='%d/%m/%Y'):
    """Filtro para formatar datas nos templates."""
    if isinstance(value, datetime):
        return value.strftime(format)
    try:
        # Tenta converter string para data e depois formatar
        return datetime.strptime(str(value).split(" ")[0], '%Y-%m-%d').strftime(format)
    except (ValueError, TypeError):
        return value

@app.template_filter('zfill')
def zfill_filter(s, width=5):
    """Filtro para adicionar zeros à esquerda (ex: 00001)."""
    return str(s).zfill(width)

def login_required(f):
    """Decorador para exigir que o usuário esteja logado."""
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

    conn = get_db_connection()
    conn.execute(
        'INSERT INTO solicitacoes (protocolo, tipo_solicitacao, dados_formulario) VALUES (?, ?, ?)',
        (protocolo, tipo_solicitacao, dados_json)
    )
    conn.commit()
    conn.close()

    flash(f'Sua solicitação de "{tipo_solicitacao}" foi enviada com sucesso! Anote seu protocolo: {protocolo}', 'success')
    return redirect(url_for('index'))


# ==================================================================
# 5. ROTAS PÚBLICAS (Páginas de Formulários e Consultas)
# ==================================================================
@app.route('/')
def index():
    return render_template('index.html')

# --- Rotas para exibir os formulários ---
@app.route('/abertura-empresa')
def abertura_empresa():
    return render_template('form_nova_empresa.html')

@app.route('/solicitacao-receituarios')
def solicitacao_receituarios():
    return render_template('form_solicitacao_receituarios.html')

@app.route('/requerimento-inicial')
def requerimento_inicial():
    return render_template('requerimento_inicial.html')

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

@app.route('/teste-calazar')
def teste_calazar():
    return render_template('form_teste_calazar.html')

# --- Rotas com busca por CNPJ ---
def buscar_empresa_por_cnpj(cnpj_input):
    """Função auxiliar para buscar uma solicitação de abertura pelo CNPJ."""
    if not cnpj_input:
        return None
    cnpj_limpo = ''.join(filter(str.isdigit, cnpj_input))
    if not cnpj_limpo:
        return None
        
    conn = get_db_connection()
    solicitacao = conn.execute(
        "SELECT * FROM solicitacoes WHERE tipo_solicitacao = 'Abertura de Empresa' AND json_extract(dados_formulario, '$.cnpj_limpo') = ? ORDER BY data_solicitacao DESC",
        (cnpj_limpo,)
    ).fetchone()
    conn.close()
    
    if not solicitacao:
        flash(f"Nenhuma solicitação de abertura encontrada para o CNPJ '{cnpj_input}'.", 'warning')
        return None
        
    dados_empresa = json.loads(solicitacao['dados_formulario'])
    dados_empresa['solicitacao_id'] = solicitacao['id']
    dados_empresa['protocolo'] = solicitacao['protocolo']
    return dados_empresa

@app.route('/alteracao-empresa', methods=['GET', 'POST'])
def alteracao_empresa():
    dados_empresa = None
    if request.method == 'POST':
        dados_empresa = buscar_empresa_por_cnpj(request.form.get('cnpj'))
    return render_template('form_alteracao.html', empresa=dados_empresa)

@app.route('/anuidade', methods=['GET', 'POST'])
def anuidade():
    dados_empresa = None
    if request.method == 'POST':
        dados_empresa = buscar_empresa_por_cnpj(request.form.get('cnpj'))
    return render_template('form_anuidade.html', empresa=dados_empresa)

@app.route('/cancelamento', methods=['GET', 'POST'])
def cancelamento():
    dados_empresa = None
    if request.method == 'POST':
        dados_empresa = buscar_empresa_por_cnpj(request.form.get('cnpj'))
    return render_template('form_cancelamento.html', empresa=dados_empresa)

# --- Rota de Consulta Unificada ---
@app.route('/consulta-unificada', methods=['GET', 'POST'])
def consulta_unificada():
    solicitacao = None
    if request.method == 'POST':
        protocolo = request.form.get('protocolo', '').strip()
        if protocolo:
            conn = get_db_connection()
            solicitacao = conn.execute('SELECT * FROM solicitacoes WHERE protocolo = ?', (protocolo,)).fetchone()
            conn.close()
            if not solicitacao:
                flash('Protocolo não encontrado. Verifique o número e tente novamente.', 'warning')
    return render_template('consulta_unificada.html', solicitacao=solicitacao)

# --- Rota da API de CNPJ ---
@app.route('/api/consulta-cnpj/<string:cnpj>')
def consulta_cnpj(cnpj):
    try:
        cnpj_limpo = ''.join(filter(str.isdigit, cnpj))
        response = requests.get(f'https://brasilapi.com.br/api/cnpj/v1/{cnpj_limpo}')
        response.raise_for_status()
        return jsonify(response.json())
    except requests.exceptions.RequestException:
        return jsonify({"erro": "CNPJ não encontrado ou API indisponível"}), 404


# ==================================================================
# 6. ROTAS DE AUTENTICAÇÃO E ÁREA ADMINISTRATIVA
# ==================================================================
users_db = {"admin": {"password": "admin123", "nome": "Administrador"}}

@app.route('/login', methods=['GET', 'POST'])
def login():
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

@app.route('/admin/solicitacoes')
@login_required
def admin_solicitacoes():
    conn = get_db_connection()
    lista_solicitacoes = conn.execute('SELECT * FROM solicitacoes ORDER BY data_solicitacao DESC').fetchall()
    conn.close()
    return render_template('admin_solicitacoes.html', solicitacoes=lista_solicitacoes)

@app.route('/admin/avaliar/<int:id>', methods=['GET', 'POST'])
@login_required
def admin_avaliar_solicitacao(id):
    conn = get_db_connection()
    if request.method == 'POST':
        novo_status = request.form.get('status')
        justificativa = request.form.get('justificativa_status', '')
        conn.execute(
            'UPDATE solicitacoes SET status = ?, justificativa_status = ? WHERE id = ?',
            (novo_status, justificativa, id)
        )
        conn.commit()
        flash(f"A solicitação foi atualizada para '{novo_status}'.", 'success')
        conn.close()
        return redirect(url_for('admin_solicitacoes'))
    
    solicitacao_raw = conn.execute('SELECT * FROM solicitacoes WHERE id = ?', (id,)).fetchone()
    conn.close()
    if not solicitacao_raw:
        abort(404, "Solicitação não encontrada.")
        
    dados_formulario = json.loads(solicitacao_raw['dados_formulario'])
    return render_template('admin_avaliacao.html', solicitacao=solicitacao_raw, dados=dados_formulario)


# ==================================================================
# 7. ROTAS PARA IMPRESSÃO E GERAÇÃO DE DOCUMENTOS
# ==================================================================
@app.route('/imprimir/documento/<protocolo>')
def imprimir_documento(protocolo):
    conn = get_db_connection()
    solicitacao = conn.execute(
        'SELECT * FROM solicitacoes WHERE protocolo = ? AND status = "Aprovado"', 
        (protocolo,)
    ).fetchone()
    conn.close()

    if not solicitacao:
        flash('Documento não encontrado ou a solicitação ainda não foi aprovada.', 'danger')
        return redirect(url_for('consulta_unificada'))

    dados = json.loads(solicitacao['dados_formulario'])
    
    # Lógica para decidir qual template de impressão usar
    template_impressao = 'licenca_impressao_generica.html' # Padrão
    if solicitacao['tipo_solicitacao'] == 'Licença para Evento':
        template_impressao = 'licenca_evento_impressao.html'
    # Adicione outras condições aqui (ex: if tipo == 'Abertura de Empresa'...)

    return render_template(template_impressao, solicitacao=solicitacao, dados=dados)

@app.route('/licenca_evento/pdf/<protocolo>')
def licenca_evento_pdf(protocolo):
    if not HTML:
        flash('A funcionalidade de gerar PDF está desativada. Contate o administrador.', 'danger')
        return redirect(url_for('consulta_unificada'))

    conn = get_db_connection()
    solicitacao = conn.execute('SELECT * FROM solicitacoes WHERE protocolo = ?', (protocolo,)).fetchone()
    conn.close()

    if not solicitacao:
        abort(404, "Licença não encontrada")

    dados = json.loads(solicitacao['dados_formulario'])
    rendered = render_template('licenca_evento_impressao.html', solicitacao=solicitacao, dados=dados)
    pdf = HTML(string=rendered).write_pdf()

    response = make_response(pdf)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'inline; filename=licenca_{protocolo}.pdf'
    return response


# ==================================================================
# 8. PONTO DE ENTRADA PARA PRODUÇÃO (GUNICORN) E DESENVOLVIMENTO
# ==================================================================
def create_app():
    """
    Função 'Factory' que o Gunicorn usa para obter a aplicação.
    O comando no Render.com deve ser: gunicorn "app:create_app()"
    """
    print("create_app() chamada pelo servidor de produção (Gunicorn).")
    with app.app_context():
        setup_database()
    return app

if __name__ == '__main__':
    """
    Este bloco só é executado quando você roda o arquivo diretamente
    com o comando: python app.py
    É usado para DESENVOLVIMENTO LOCAL. O Gunicorn IGNORA este bloco.
    """
    print("===================================================")
    print(">>> EXECUTANDO EM MODO DE DESENVOLVIMENTO LOCAL <<<")
    print("===================================================")
    with app.app_context():
        setup_database() # Garante que o DB está pronto antes de rodar
    app.run(debug=True, host="0.0.0.0", port=5001)

    # Garante que o banco de dados e as tabelas sejam criados ao iniciar
    setup_database()
    app.run(debug=True, port=5001)
    
    if __name__ == "__main__":
    app.run(debug=True)
