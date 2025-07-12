from datetime import date
from yourapp import db  # substitua por seu import correto

class AlvaraSanitario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    protocolo = db.Column(db.String(20))
    empresa_id = db.Column(db.Integer)  # ou relacionamento, se usar foreign key
    data_emissao = db.Column(db.Date, default=date.today)
    data_validade = db.Column(db.Date)