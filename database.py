import sqlite3
from werkzeug.security import generate_password_hash

NOME_DO_ARQUIVO_DB = "vigilancia.db"

def get_db_connection():
    """Cria e retorna uma conexão com a base de dados."""
    conn = sqlite3.connect(NOME_DO_ARQUIVO_DB)
    conn.row_factory = sqlite3.Row
    return conn

def setup_database():
    """Cria todas as tabelas necessárias se elas não existirem."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    print("--- A verificar a configuração da base de dados...")
    
    # Tabela de utilizadores
    cursor.execute("CREATE TABLE IF NOT EXISTS utilizadores (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT NOT NULL UNIQUE, password TEXT NOT NULL);")
    
    # Tabela de Empresas
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS empresas (
            id INTEGER PRIMARY KEY AUTOINCREMENT, razao_social TEXT NOT NULL, nome_fantasia TEXT,
            cnpj TEXT NOT NULL UNIQUE, situacao TEXT DEFAULT 'Ativa', cnae_principal TEXT
        );
    """)
    
    # Tabela de Licenças
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS licencas (
            id INTEGER PRIMARY KEY AUTOINCREMENT, empresa_id INTEGER NOT NULL, numero_licenca TEXT NOT NULL UNIQUE,
            data_emissao DATE NOT NULL, data_validade DATE NOT NULL, situacao TEXT NOT NULL,
            FOREIGN KEY (empresa_id) REFERENCES empresas (id)
        );
    """)
    
    print("--- Tabelas verificadas/criadas.")

    # Insere o utilizador 'admin' se ele não existir
    cursor.execute("SELECT * FROM utilizadores WHERE username = 'admin'")
    if cursor.fetchone() is None:
        hashed_password = generate_password_hash('admin123')
        cursor.execute("INSERT INTO utilizadores (username, password) VALUES (?, ?)", ('admin', hashed_password))
        print("--- Utilizador 'admin' criado.")
    
    conn.commit()
    conn.close()
    print("--- Configuração da base de dados finalizada.")

