# routes/vigilancia.py

from flask import Blueprint, render_template

vigilancia_bp = Blueprint('vigilancia', __name__, url_prefix='/dashboard')

@vigilancia_bp.route('/')
# A linha @login_required foi removida daqui
def dashboard():
    return render_template('vigilancia/dashboard.html')