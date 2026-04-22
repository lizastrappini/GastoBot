from database import db
from datetime import datetime

class Gasto(db.Model):
    __tablename__ = "Gastos"
    Id = db.Column(db.Integer, primary_key=True)
    IdCategoria = db.Column(db.Integer, db.ForeignKey("Categorias.Id"), nullable=False)
    Monto = db.Column(db.Numeric(10, 2), nullable=False)
    IdUsuario = db.Column(db.Integer, db.ForeignKey("Usuario.Id"), nullable=False)
    Fecha = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)