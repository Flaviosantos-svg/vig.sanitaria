# app.py - Sistema de Vigilância Sanitária Municipal

import os
import sqlite3
import json
from functools import wraps
from datetime import date
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, Blueprint
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
from flask import Blueprint, request, jsonify
from api import api 
from app.models import Cnae
from models import CnaeExigencia
from app import db

api = Blueprint('api', __name__)
app = Flask(__name__)
app.register_blueprint(api)
if __name__ == '__main__':
    app.run(debug=True)

# ------------------------------------------------------------------
# CONFIGURAÇÕES INICIAIS
# ------------------------------------------------------------------
app = Flask(__name__)
app.secret_key = 'sua-chave-secreta-super-segura-aqui'
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
NOME_DO_ARQUIVO_DB = "vigilancia.db"

# ------------------------------------------------------------------
# BANCO DE DADOS E SETUP
# ------------------------------------------------------------------
def get_db_connection():
    conn = sqlite3.connect(NOME_DO_ARQUIVO_DB)
    conn.row_factory = sqlite3.Row
    return conn

def setup_database():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS utilizadores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cnae (
            secao TEXT,
            codigo TEXT PRIMARY KEY,
            descricao TEXT,
            competencia TEXT,
            risco TEXT,
            necessita_rt TEXT,
            perguntas TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS empresas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            razao_social TEXT NOT NULL,
            cnpj TEXT NOT NULL UNIQUE,
            telefone TEXT, email TEXT,
            endereco_rua TEXT, endereco_numero TEXT, endereco_bairro TEXT, endereco_cidade TEXT,
            cnae_primario_codigo TEXT,
            cnaes_secundarios_json TEXT,
            data_cadastro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    if cursor.execute("SELECT id FROM utilizadores WHERE username = 'admin'").fetchone() is None:
        senha_hash = generate_password_hash('admin123')
        cursor.execute("INSERT INTO utilizadores (username, password) VALUES (?, ?)", ('admin', senha_hash))
    conn.commit()
    conn.close()

# ------------------------------------------------------------------
# DECORADOR DE LOGIN
# ------------------------------------------------------------------
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            flash('Faça login para acessar.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# ------------------------------------------------------------------
# ROTAS PÚBLICAS
# ------------------------------------------------------------------
@app.route('/')
def index(): return render_template('index.html')

@app.route('/requerimento_inicial')
def requerimento_inicial(): return render_template('requerimento_inicial.html')

@app.route('/abertura_empresa')
def abertura_empresa(): return render_template('form_nova_empresa.html')

@app.route('/alteracao_empresa', methods=['GET', 'POST'])
def alteracao_empresa(): return render_template('form_alteracao.html', empresa=None)

@app.route('/anuidade', methods=['GET', 'POST'])
def anuidade(): return render_template('form_anuidade.html', empresa=None)

@app.route('/cancelamento', methods=['GET', 'POST'])
def cancelamento(): return render_template('form_cancelamento.html', empresa=None)

@app.route('/licenca_evento')
def licenca_evento(): return render_template('form_licenca_evento.html')

@app.route('/dispensa_licenca', methods=['GET', 'POST'])
def dispensa_licenca(): return render_template('form_dispensa_licenca.html', empresa=None)

@app.route('/denuncia')
def denuncia(): return render_template('form_denuncia.html')

@app.route('/registrar_denuncia')
def registrar_denuncia(): return render_template('form_denuncia.html')

@app.route('/consulta_licencas', methods=['GET', 'POST'])
def consulta_licencas(): return render_template('form_consulta_licenca.html', licencas=[])

@app.route('/vistorias_denuncias')
def vistorias_denuncias(): return render_template('vistorias_denuncias_menu.html')

@app.route('/vistorias_fiscalizacoes')
def vistorias_fiscalizacoes(): return render_template('form_vistoria.html')

@app.route('/licenca_instituicao_publica', methods=['GET', 'POST'])
def licenca_instituicao_publica(): return render_template('form_licenca_instituicao.html', empresa=None)

@app.route('/teste_calazar')
def teste_calazar(): return render_template('form_teste_calazar.html')

@app.route('/sucesso')
def sucesso():
    msg = request.args.get('msg', 'Operação realizada com sucesso!')
    return render_template('sucesso.html', mensagem=msg)

# ------------------------------------------------------------------
# LOGIN
# ------------------------------------------------------------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = get_db_connection()
        user = conn.execute("SELECT * FROM utilizadores WHERE username = ?", (username,)).fetchone()
        conn.close()
        if user and check_password_hash(user['password'], password):
            session['logged_in'] = True
            session['user_name'] = user['username']
            return redirect(url_for('admin_dashboard'))
        flash('Usuário ou senha inválidos.', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Logout efetuado com sucesso.', 'info')
    return redirect(url_for('index'))

# ------------------------------------------------------------------
# DASHBOARD
# ------------------------------------------------------------------
@app.route('/admin')
@login_required
def admin_dashboard(): return render_template('admin_index.html')

@app.route('/admin/menu')
@login_required
def admin_menu(): return redirect(url_for('admin_dashboard'))

# ------------------------------------------------------------------
# SALVAR EMPRESA
# ------------------------------------------------------------------
@app.route('/salvar_empresa', methods=['POST'])
@login_required
def salvar_empresa():
    try:
        cnpj = request.form.get('cnpj')
        razao_social = request.form.get('razao_social')
        cnae_primario = request.form.get('cnae_primario_codigo')
        cnaes_secundarios_str = request.form.getlist('cnae_secundario_codigo')

        cnaes_para_verificar = []
        if cnae_primario:
            cnaes_para_verificar.append({'codigo': cnae_primario.replace('/', '').replace('-', '').replace('.', '')})
        for cnae_sec in cnaes_secundarios_str:
            if cnae_sec:
                cnaes_para_verificar.append({'codigo': cnae_sec.replace('/', '').replace('-', '').replace('.', '')})

        conn = get_db_connection()
        cursor = conn.cursor()
        novos = 0
        for cnae in cnaes_para_verificar:
            cursor.execute("SELECT COUNT(*) FROM cnae WHERE codigo = ?", (cnae['codigo'],))
            if cursor.fetchone()[0] == 0:
                cursor.execute("INSERT INTO cnae (codigo, descricao) VALUES (?, ?)", (cnae['codigo'], 'Descricao pendente'))
                novos += 1

        cursor.execute("""
            INSERT INTO empresas (cnpj, razao_social, cnae_primario_codigo, cnaes_secundarios_json)
            VALUES (?, ?, ?, ?)
        """, (cnpj, razao_social, cnae_primario, json.dumps(cnaes_secundarios_str)))
        conn.commit()
        conn.close()

        flash("Requerimento salvo com sucesso!", "success")
        if novos:
            flash(f"{novos} CNAE(s) novos adicionados. Configure-os.", "warning")
        return redirect(url_for('admin_cnae_config'))
    except Exception as e:
        flash(f"Erro ao salvar: {e}", "danger")
        return redirect(url_for('abertura_empresa'))

# ------------------------------------------------------------------
# CONFIGURAÇÃO DE CNAE
# ------------------------------------------------------------------
@app.route('/admin/config/cnae', methods=['GET', 'POST'])
@login_required
def admin_cnae_config():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM cnae ORDER BY secao, codigo")
    lista = cursor.fetchall()
    conn.close()
    secoes = {}
    for row in lista:
        if not row['secao']: continue
        secoes.setdefault(row['secao'], []).append(dict(row))
    return render_template('admin_cnae_config.html', cnae_sections=[{'secao': k, 'subclasses': v} for k, v in secoes.items()])

# ------------------------------------------------------------------
# API CNAE CONFIGS
# ------------------------------------------------------------------
@app.route('/api/get_cnae_configs', methods=['POST'])
@login_required
def get_cnae_configs():
    try:
        data = request.get_json()
        codigos = [str(c).replace('/', '').replace('-', '').replace('.', '') for c in data.get('cnaes', []) if c]
        if not codigos: return jsonify([])
        conn = get_db_connection()
        placeholders = ','.join('?' * len(codigos))
        rows = conn.execute(f"SELECT * FROM cnae WHERE codigo IN ({placeholders})", codigos).fetchall()
        conn.close()
        return jsonify([dict(r) for r in rows])
    except Exception as e:
        return jsonify({'error': str(e)}), 500
# ------------------------------------------------------------------
# API CNAE CONFIGS EXIGENCIAS
# ------------------------------------------------------------------
@api.route('/api/cnae/exigencias', methods=['POST'])
def obter_exigencias_cnae():
    data = request.get_json()
    cnaes = data.get('cnaes', [])

    if not cnaes:
        return jsonify({"error": "Nenhum código CNAE fornecido"}), 400

    cnaes_clean = [c.strip().replace('.', '').replace('-', '').replace('/', '') for c in cnaes]

    resultados = Cnae.query.filter(Cnae.codigo.in_(cnaes_clean)).all()

    lista_exigencias = []
    for cnae in resultados:
        lista_exigencias.append({
            "codigo": cnae.codigo,
            "descricao": cnae.descricao,
            "competencia": cnae.competencia,
            "risco": cnae.risco,
            "necessita_rt": cnae.necessita_rt,
            "perguntas": cnae.perguntas
        })

    return jsonify(lista_exigencias)
# ------------------------------------------------------------------
# EXECUÇÃO
# ------------------------------------------------------------------
if __name__ == '__main__':
    setup_database()
    app.run(debug=True, port=5001)
