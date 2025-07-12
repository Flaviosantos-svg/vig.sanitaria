from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.security import check_password_hash
from database import get_db_connection

public_bp = Blueprint('public', __name__)

@public_bp.route('/')
def index(): 
    return render_template('index.html')

@public_bp.route('/requerimento_inicial')
def requerimento_inicial(): 
    return render_template('requerimento_inicial.html')

@public_bp.route('/abertura_empresa')
def abertura_empresa():
    return render_template('form_nova_empresa.html')

@public_bp.route('/alteracao_empresa', methods=['GET', 'POST'])
def alteracao_empresa():
    empresa = None
    if request.method == 'POST':
        cnpj = request.form.get('cnpj', '').strip()
        conn = get_db_connection()
        empresa = conn.execute("SELECT * FROM empresas WHERE cnpj = ?", (cnpj,)).fetchone()
        conn.close()
        if not empresa:
            flash(f"Nenhuma empresa encontrada com o CNPJ '{cnpj}'.", 'warning')
    return render_template('form_alteracao.html', empresa=empresa)

@public_bp.route('/anuidade', methods=['GET', 'POST'])
def anuidade():
    empresa = None
    if request.method == 'POST':
        cnpj = request.form.get('cnpj', '').strip()
        conn = get_db_connection()
        empresa = conn.execute("SELECT * FROM empresas WHERE cnpj = ?", (cnpj,)).fetchone()
        conn.close()
        if not empresa:
            flash(f"Nenhuma empresa encontrada com o CNPJ '{cnpj}'.", 'warning')
    return render_template('form_anuidade.html', empresa=empresa)

@public_bp.route('/cancelamento', methods=['GET', 'POST'])
def cancelamento():
    empresa = None
    if request.method == 'POST':
        cnpj = request.form.get('cnpj', '').strip()
        conn = get_db_connection()
        empresa = conn.execute("SELECT * FROM empresas WHERE cnpj = ?", (cnpj,)).fetchone()
        conn.close()
        if not empresa:
            flash(f"Nenhuma empresa encontrada com o CNPJ '{cnpj}'.", 'warning')
    return render_template('form_cancelamento.html', empresa=empresa)

@public_bp.route('/licenca_evento')
def licenca_evento():
    return render_template('form_licenca_evento.html')

@public_bp.route('/dispensa_licenca', methods=['GET', 'POST'])
def dispensa_licenca():
    empresa = None
    if request.method == 'POST':
        cnpj = request.form.get('cnpj', '').strip()
        conn = get_db_connection()
        empresa = conn.execute("SELECT * FROM empresas WHERE cnpj = ?", (cnpj,)).fetchone()
        conn.close()
        if not empresa:
            flash(f"Nenhuma empresa encontrada com o CNPJ '{cnpj}'.", 'warning')
    return render_template('form_dispensa_licenca.html', empresa=empresa)

@public_bp.route('/denuncia')
def denuncia():
    return render_template('form_denuncia.html')

@public_bp.route('/consulta_licencas')
def consulta_licencas():
    return render_template('form_consulta_licenca.html', licencas=[])

@public_bp.route('/vistorias_denuncias')
def vistorias_denuncias():
    return render_template('vistorias_denuncias_menu.html')

@public_bp.route('/licenca_instituicao_publica')
def licenca_instituicao_publica():
    return render_template('form_licenca_instituicao.html')

@public_bp.route('/teste_calazar')
def teste_calazar():
    return render_template('form_teste_calazar.html')

@public_bp.route('/sucesso')
def sucesso():
    mensagem = request.args.get('msg', 'Operação realizada com sucesso!')
    return render_template('sucesso.html', mensagem=mensagem)

@public_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM utilizadores WHERE username = ?', (username,)).fetchone()
        conn.close()
        if user and check_password_hash(user['password'], password):
            session['logged_in'] = True
            session['username'] = user['username']
            return redirect(url_for('admin.dashboard'))
        else:
            flash('Credenciais inválidas.', 'danger')
    return render_template('login.html')

@public_bp.route('/logout')
def logout():
    session.clear()
    flash('Logout efetuado com sucesso.', 'info')
    return redirect(url_for('public.index'))
