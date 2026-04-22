from database import db

class Usuario(db.Model):
    __tablename__ = "Usuario"
    Id = db.Column(db.Integer, primary_key=True)
    IdChat = db.Column(db.Integer, nullable=False)
    IdTipo = db.Column(db.Integer, nullable=False, default=1)
    Nombre = db.Column(db.String(50), nullable=False)
    FechaBaja = db.Column(db.DateTime, nullable=True, default=None)
    categorias = db.relationship("Categoria", backref="usuario", lazy=True)
    gastos = db.relationship("Gasto", backref="usuario", lazy=True)