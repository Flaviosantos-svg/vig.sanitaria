# ==================================================================
#       FICHEIRO: app.py (VERSÃO FINAL, CORRIGIDA E ORGANIZADA)
# ==================================================================
import os
import sqlite3
import json
from datetime import datetime
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, abort
import requests
from werkzeug.utils import secure_filename

# --- 1. CONFIGURAÇÃO INICIAL DO FLASK ---
app = Flask(__name__)
app.secret_key = 'sua_chave_secreta_super_dificil'
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)


@app.route("/")
def home():
    return "Servidor Flask rodando!"

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

    # Tabela UNIFICADA para todas as solicitações (a única necessária para o novo sistema)
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

    conn.commit()
    conn.close()
    print("Banco de dados configurado com sucesso.")

# Exemplo de base de dados fictícia para simular
licencas_eventos = {
    1: {
        "organizador_nome": "João Silva",
        "organizador_doc": "123.456.789-00",
        "organizador_empresa": "Eventos XYZ",
        "organizador_tel": "(11) 99999-9999",
        "organizador_email": "joao@email.com",
        "organizador_endereco": "Rua das Flores, 123, Centro",

        "evento_nome": "Festa Junina",
        "evento_tipo": "Cultural",
        "evento_tipo_outro": "",
        "evento_data_inicio": "2025-06-15",
        "evento_data_fim": "2025-06-16",
        "evento_horario": "18:00 às 23:00",
        "evento_local": "Praça Central",
        "evento_publico_estimado": 500,
        "evento_estrutura_temp": ["Tendas", "Palco"],
        "evento_estrutura_outro": "Iluminação especial",

        "servico_alimentos": "Sim",
        "servico_alimentos_detalhes": "Barracas de pastel e quentão",
        "servico_agua_potavel": "Sim",
        "servico_residuos": "Lixeiras distribuídas no local e coleta diária",
        "servico_sanitarios": 6,

        "local_resp_nome": "Maria Oliveira",
        "local_resp_cpf": "987.654.321-00",
        "local_resp_setor": "Vigilância Sanitária",
        "local_resp_contato": "(11) 98888-8888",

        "data_emissao": "2025-06-01",
        "data_validade": "2025-06-16"
    }
}

    # Adicione aqui outras tabelas que seu sistema precise, como 'licencas_emitidas', etc.



# --- 3. DECORADOR DE LOGIN ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            flash('É necessário fazer login para acessar esta página.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# --- 4. DADOS SIMULADOS (Para testes e partes não migradas) ---
users_db = {
    "admin": {"password": "admin123", "nome": "Administrador"}
}

# --- 5. FUNÇÕES AUXILIARES ---
def gerar_protocolo():
    """Gera um protocolo único baseado na data/hora."""
    return f"VISA-{datetime.now().strftime('%Y%m%d%H%M%S')}"

# ==================================================================
# 6. ROTA UNIFICADA PARA RECEBER DADOS DOS FORMULÁRIOS
# ==================================================================
@app.route('/submeter_solicitacao', methods=['POST'])
def submeter_solicitacao():
    protocolo = gerar_protocolo()
    tipo_solicitacao = request.form.get('tipo_solicitacao', 'Desconhecido')

    # Salva todos os dados do formulário em formato JSON
    dados_dict = dict(request.form)
    
    # Adiciona uma versão limpa do CNPJ (só números) para facilitar buscas futuras
    if 'cnpj' in dados_dict:
        dados_dict['cnpj_limpo'] = ''.join(filter(str.isdigit, dados_dict['cnpj']))

    dados_dict.pop('tipo_solicitacao', None)
    dados_json = json.dumps(dados_dict, indent=4, ensure_ascii=False)

    conn = get_db_connection()
    conn.execute(
        'INSERT INTO solicitacoes (protocolo, tipo_solicitacao, dados_formulario) VALUES (?, ?, ?)',
        (protocolo, tipo_solicitacao, dados_json)
    )
    conn.commit()
    conn.close()

    flash(f'Sua solicitação de "{tipo_solicitacao}" foi enviada com sucesso! Anote seu número de protocolo para acompanhamento: {protocolo}', 'success')
    return redirect(url_for('index'))

# ==================================================================
# 7. ROTAS PÚBLICAS (Páginas de Formulários e Consulta)
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

# --- ROTAS RESTAURADAS PARA EVITAR ERROS ---
@app.route('/requerimento-inicial')
def requerimento_inicial():
    return render_template('requerimento_inicial.html')

@app.route('/alteracao-empresa', methods=['GET', 'POST'])
def alteracao_empresa():
    dados_empresa = None
    if request.method == 'POST':
        cnpj_input = request.form.get('cnpj', '').strip()
        if cnpj_input:
            # Limpa o CNPJ digitado pelo usuário para a busca
            cnpj_limpo = ''.join(filter(str.isdigit, cnpj_input))
            
            conn = get_db_connection()
            # Busca na tabela de solicitações usando o CNPJ limpo
            # Nota: json_extract requer SQLite 3.9.0+
            solicitacao = conn.execute(
                "SELECT * FROM solicitacoes WHERE tipo_solicitacao = 'Abertura de Empresa' AND json_extract(dados_formulario, '$.cnpj_limpo') = ?",
                (cnpj_limpo,)
            ).fetchone()
            conn.close()
            
            if not solicitacao:
                flash(f"Nenhuma solicitação de abertura de empresa encontrada para o CNPJ '{cnpj_input}'.", 'warning')
            else:
                # Se encontrou, extrai os dados do JSON para usar no formulário
                dados_empresa = json.loads(solicitacao['dados_formulario'])
                # Adiciona o ID e o protocolo da solicitação para referência futura
                dados_empresa['solicitacao_id'] = solicitacao['id']
                dados_empresa['protocolo'] = solicitacao['protocolo']

    # Passa os dados da empresa (se encontrados) para o template
    return render_template('form_alteracao.html', empresa=dados_empresa)

@app.route('/anuidade', methods=['GET', 'POST'])
def anuidade():
    dados_empresa = None
    if request.method == 'POST':
        cnpj_input = request.form.get('cnpj', '').strip()
        if cnpj_input:
            cnpj_limpo = ''.join(filter(str.isdigit, cnpj_input))
            conn = get_db_connection()
            solicitacao = conn.execute(
                "SELECT * FROM solicitacoes WHERE tipo_solicitacao = 'Abertura de Empresa' AND json_extract(dados_formulario, '$.cnpj_limpo') = ?",
                (cnpj_limpo,)
            ).fetchone()
            conn.close()
            if not solicitacao:
                flash(f"Nenhuma empresa encontrada para o CNPJ '{cnpj_input}'.", 'warning')
            else:
                dados_empresa = json.loads(solicitacao['dados_formulario'])
                dados_empresa['solicitacao_id'] = solicitacao['id']
    return render_template('form_anuidade.html', empresa=dados_empresa)

@app.route('/dispensa-licenca')
def dispensa_licenca():
    return render_template('form_dispensa_licenca.html')

@app.route('/licenca-evento', methods=['GET', 'POST'])
def licenca_evento():
    if request.method == 'POST':
        # Esta rota agora redireciona para a rota unificada, que vai gerar o protocolo.
        # Para isso funcionar, o formulário HTML precisa ser ajustado.
        return submeter_solicitacao()
    # Se o método for GET, apenas exibe o formulário.
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

@app.route('/cancelamento', methods=['GET', 'POST'])
def cancelamento():
    dados_empresa = None
    if request.method == 'POST':
        cnpj_input = request.form.get('cnpj', '').strip()
        if cnpj_input:
            cnpj_limpo = ''.join(filter(str.isdigit, cnpj_input))
            conn = get_db_connection()
            solicitacao = conn.execute(
                "SELECT * FROM solicitacoes WHERE tipo_solicitacao = 'Abertura de Empresa' AND json_extract(dados_formulario, '$.cnpj_limpo') = ?",
                (cnpj_limpo,)
            ).fetchone()
            conn.close()
            if not solicitacao:
                flash(f"Nenhuma empresa encontrada para o CNPJ '{cnpj_input}'.", 'warning')
            else:
                dados_empresa = json.loads(solicitacao['dados_formulario'])
                dados_empresa['solicitacao_id'] = solicitacao['id']
    return render_template('form_cancelamento.html', empresa=dados_empresa)

@app.route('/consulta-licencas')
def consulta_licencas():
    # A melhor prática agora é redirecionar para a página unificada
    return redirect(url_for('consulta_unificada'))
# --- FIM DAS ROTAS RESTAURADAS ---


# --- Rota de Consulta Unificada ---
@app.route('/consulta-unificada', methods=['GET', 'POST'])
def consulta_unificada():
    solicitacao = None
    search_type = request.form.get('search_type', 'protocolo')

    if request.method == 'POST':
        if search_type == 'protocolo':
            protocolo = request.form.get('protocolo', '').strip()
            if protocolo:
                conn = get_db_connection()
                solicitacao = conn.execute('SELECT * FROM solicitacoes WHERE protocolo = ?', (protocolo,)).fetchone()
                conn.close()
                if not solicitacao:
                    flash('Protocolo não encontrado. Verifique o número e tente novamente.', 'warning')
    
    return render_template('consulta_unificada.html', 
                           solicitacao=solicitacao, 
                           search_type=search_type)

# --- Rota da API de CNPJ ---
@app.route('/api/consulta-cnpj/<string:cnpj>')
def consulta_cnpj(cnpj):
    try:
        cnpj_limpo = ''.join(filter(str.isdigit, cnpj))
        response = requests.get(f'https://brasilapi.com.br/api/cnpj/v1/{cnpj_limpo}')
        response.raise_for_status()
        return jsonify(response.json())
    except requests.exceptions.RequestException:
        return jsonify({"erro": "CNPJ não encontrado ou inválido"}), 404

# ==================================================================
# 8. ROTAS DE AUTENTICAÇÃO E ADMINISTRAÇÃO
# ==================================================================
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

@app.route('/admin/empresas')
@login_required
def admin_empresas_lista():
    # No futuro, esta página pode ter uma lógica mais complexa para listar apenas empresas com licença ativa.
    # Por enquanto, redirecionar para a lista de solicitações é uma solução funcional.
    return redirect(url_for('admin_solicitacoes'))

@app.route('/admin/cnae')
@login_required
def admin_cnae_lista():
    # Placeholder para a página de gerenciamento de CNAEs
    return "Página de Gerenciamento de CNAEs"

# ROTA ADICIONADA PARA CORRIGIR O ERRO
@app.route('/admin/relatorios')
@login_required
def admin_relatorios():
    # No futuro, esta rota buscará dados reais do banco.
    # Por enquanto, usamos dados de exemplo.
    relatorios_exemplo = [
        {'tipo': 'Vistoria', 'data': '11/07/2025', 'alvo': 'Supermercado Preço Bom'},
        {'tipo': 'Atendimento de Denúncia', 'data': '10/07/2025', 'alvo': 'Padaria Pão Quente'}
    ]
    return render_template('admin_relatorios.html', relatorios=relatorios_exemplo)

@app.route('/admin/avaliar/<int:id>', methods=['GET', 'POST'])
@login_required
def admin_avaliar_solicitacao(id):
    conn = get_db_connection()
    
    # Lógica para ATUALIZAR o status quando o formulário for enviado
    if request.method == 'POST':
        novo_status = request.form.get('status')
        justificativa = request.form.get('justificativa_status')
        
        conn.execute(
            'UPDATE solicitacoes SET status = ?, justificativa_status = ? WHERE id = ?',
            (novo_status, justificativa, id)
        )
        conn.commit()
        
        # Futuramente, se o status for 'Aprovado', aqui chamaremos a função para gerar o alvará
        # if novo_status == 'Aprovado':
        #     gerar_alvara(id)

        flash(f"A solicitação foi atualizada para '{novo_status}'.", 'success')
        return redirect(url_for('admin_solicitacoes'))

    # Lógica para EXIBIR os detalhes da solicitação (quando a página é carregada)
    solicitacao_raw = conn.execute('SELECT * FROM solicitacoes WHERE id = ?', (id,)).fetchone()
    conn.close()
    
    if not solicitacao_raw:
        return "Solicitação não encontrada!", 404
        
    # Converte o texto JSON de volta para um dicionário Python para ser usado no template
    dados_formulario = json.loads(solicitacao_raw['dados_formulario'])
    
    return render_template('admin_avaliacao.html', solicitacao=solicitacao_raw, dados=dados_formulario)

# IMPRIMIR ALVARA#

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

    # Carrega os dados do formulário do JSON para usar no template do alvará
    dados_empresa = json.loads(solicitacao['dados_formulario'])
    
    # Renderiza um novo template que é formatado para impressão
    return render_template('licenca_evento_impressao.html', solicitacao=solicitacao, empresa=dados_empresa)

# ROTA FLASH #

@app.route('/emitir_alvara/<int:solicitacao_id>', methods=['GET', 'POST'])
def emitir_alvara(solicitacao_id):
    data_emissao = datetime.now().date()
    validade_default = datetime.strptime(f'31/12/{data_emissao.year}', '%d/%m/%Y').date()

    if request.method == 'POST':
        data_validade = request.form.get('data_validade')

        try:
            data_validade = datetime.strptime(data_validade, '%Y-%m-%d').date()
        except:
            data_validade = validade_default  # fallback

        novo_alvara = AlvaraSanitario(
            protocolo=f'ALV-{solicitacao_id:05d}-{data_emissao.year}',
            empresa_id=123,  # substitua pelo ID real da empresa
            data_emissao=data_emissao,
            data_validade=data_validade
        )

        db.session.add(novo_alvara)
        db.session.commit()

        return redirect(url_for('ver_alvara', alvara_id=novo_alvara.id))

    return render_template(
        'form_emitir_alvara.html',
        solicitacao_id=solicitacao_id,
        data_emissao=data_emissao,
        data_validade_default=validade_default.strftime('%Y-%m-%d')  # formato para <input type="date">
    )

@app.template_filter('zfill')
def zfill_filter(s, width=5):
    return str(s).zfill(width)


@app.route('/licenca_evento/imprimir/<int:id>')
def imprimir_licenca(id):
    licenca = licencas_eventos.get(id)
    if not licenca:
        abort(404)
    return render_template('licenca_evento_impressao.html', **licenca)

@app.route('/licenca_evento/pdf/<int:id>')
def licenca_evento_pdf(id):
    licenca = licencas_eventos.get(id)
    if not licenca:
        abort(404)
    rendered = render_template('licenca_evento_impressao.html', **licenca)
    pdf = HTML(string=rendered).write_pdf()

    response = make_response(pdf)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'inline; filename=licenca_evento_{id}.pdf'
    return response

# ==================================================================
# 9. INICIAR A APLICAÇÃO
# ==================================================================
if __name__ == '__main__':
    # Garante que o banco de dados e as tabelas sejam criados ao iniciar
    setup_database()
    app.run(debug=True, port=5001)
    