from database import db

class Categoria(db.Model):
    __tablename__ = "Categorias"
    Id = db.Column(db.Integer, primary_key=True)
    Nombre = db.Column(db.String(50), nullable=False)
    IdUsuario = db.Column(db.Integer, db.ForeignKey("Usuario.Id"), nullable=False)
    gastos = db.relationship("Gasto", backref="categoria", lazy=True)