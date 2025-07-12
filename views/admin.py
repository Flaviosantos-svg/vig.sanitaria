from flask import Blueprint, render_template, request, redirect, url_for, session, flash
import sqlite3
from database import get_db_connection
from functools import wraps

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            flash('É necessário fazer login para aceder a esta página.', 'warning')
            return redirect(url_for('public.login'))
        return f(*args, **kwargs)
    return decorated_function

@admin_bp.route('/dashboard')
@login_required
def dashboard():
    """Renderiza o novo dashboard de administração."""
    return render_template('admin_index.html')

@admin_bp.route('/empresas')
@login_required
def empresas_lista():
    conn = get_db_connection()
    empresas = conn.execute("SELECT * FROM empresas ORDER BY razao_social").fetchall()
    conn.close()
    return render_template('admin_empresas.html', empresas=empresas)
