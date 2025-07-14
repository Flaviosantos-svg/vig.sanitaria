from models import Cnae


class Cnae(db.Model):
    __tablename__ = 'cnae'

    codigo = db.Column(db.String, primary_key=True)
    secao = db.Column(db.String, nullable=True)
    descricao = db.Column(db.String, nullable=True)
    competencia = db.Column(db.String, nullable=True)
    risco = db.Column(db.String, nullable=True)
    necessita_rt = db.Column(db.String, nullable=True)
    perguntas = db.Column(db.Text, nullable=True)
