from flask import Blueprint, request, jsonify
from your_flask_app import db  # Ajuste o import para o seu app
from your_flask_app.models import CnaeExigencia  # Ajuste o import para o seu modelo

api = Blueprint('api', __name__)

@api.route('/api/get_cnae_configs', methods=['POST'])
def get_cnae_configs():
    try:
        data = request.get_json()
        cnaes = data.get('cnaes', [])
        if not cnaes:
            return jsonify([])

        # Limpa os códigos dos CNAEs para formato padrão (sem pontuação)
        cnae_codes_clean = [str(c).strip().replace('/', '').replace('-', '').replace('.', '') for c in cnaes]

        # Consulta no banco as exigências para os CNAEs informados
        exigencias = CnaeExigencia.query.filter(CnaeExigencia.codigo.in_(cnae_codes_clean)).all()

        resposta = []
        for cnae in exigencias:
            resposta.append({
                "codigo": cnae.codigo,
                "descricao": cnae.descricao,
                "perguntas": cnae.perguntas,
                "necessita_rt": cnae.necessita_rt
            })

        return jsonify(resposta)
    except Exception as e:
        return jsonify({"error": "Erro interno no servidor", "message": str(e)}), 500
