from flask import Flask, request, jsonify
from dotenv import load_dotenv
from database import db
import requests
import os
from datetime import datetime, timedelta

load_dotenv()

app = Flask(__name__)

app.config["SQLALCHEMY_DATABASE_URI"] = (
    f"mysql+pymysql://{os.getenv('MYSQL_USER')}:{os.getenv('MYSQL_PASSWORD')}"
    f"@{os.getenv('MYSQL_HOST')}:{os.getenv('MYSQL_PORT', '3306')}/{os.getenv('MYSQL_DATABASE')}"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

GRAFANA_URL = os.getenv("GRAFANA_URL")  
GRAFANA_DASHBOARD_ID = os.getenv("GRAFANA_DASHBOARD_ID") 

db.init_app(app)

from Model import Usuario, Categoria, Gasto

TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_API = f"https://api.telegram.org/bot{TOKEN}"


def enviarMensaje(chat_id, texto, parse_mode=None):
    payload = {
        "chat_id": chat_id,
        "text": texto
    }
    if parse_mode:
        payload["parse_mode"] = parse_mode
    requests.post(f"{TELEGRAM_API}/sendMessage", json=payload)

"""def getUsuario(chat_id):
    usuario = Usuario.query.filter_by(IdChat=chat_id).first()
    return usuario

def nuevoUsuario(chat_id, nombre):
    usuario = Usuario(Nombre = nombre, IdChat = chat_id, IdTipo=1)
    db.session.add(usuario)
    db.session.commit()
    return usuario"""

def getOrCreateUsuario(chat_id, nombre):
    usuario = Usuario.query.filter_by(IdChat=chat_id).first()
    
    if not usuario:
        usuario = Usuario(Nombre=nombre, IdChat=chat_id, IdTipo=1)
        db.session.add(usuario)
        db.session.commit()
    
    return usuario

def getCategoria(nombre, id_usuario):
    nombre = nombre.strip().lower()
    categoria = Categoria.query.filter(db.func.lower(Categoria.Nombre) == nombre, Categoria.IdUsuario == id_usuario).first()
    
    if not categoria:
        categoria = Categoria(Nombre=nombre, IdUsuario=id_usuario)
        db.session.add(categoria)
        db.session.commit()
    return categoria

def nuevoGasto(usuario, chat_id, args):
    try:
        partes = args.split(" ", 1)
        monto = float(partes[0])
        categoria_nombre = partes[1].strip().lower()
    except:
        enviarMensaje(chat_id, "🚫 Formato incorrecto. Usá: /gasto 100.50 comida")
        return

    if monto <= 0:
        enviarMensaje(chat_id, "🚫 El monto debe ser un número positivo")
        return
    
    if not categoria_nombre:
        enviarMensaje(chat_id, "🚫 Debés indicar una categoría")
        return
    
    categoria = getCategoria(categoria_nombre, usuario.Id)

    hace_un_minuto = datetime.utcnow() - timedelta(minutes=1)
    
    existe = Gasto.query.filter(db.func.abs(db.cast(Gasto.Monto, db.Float) - monto) < 0.001, Gasto.IdUsuario == usuario.Id, Gasto.IdCategoria == categoria.Id,Gasto.Fecha >= hace_un_minuto).first()
    
    if existe:
        enviarMensaje(chat_id, "✋ Ya registraste un gasto por el mismo monto y categoria hace menos de 1 minuto! Verificá tus gastos recientes")
        return
    
    if monto <= 0:
        enviarMensaje(chat_id, "🚫 El monto debe ser un número positivo")
        return
    

    gasto = Gasto(IdCategoria=categoria.Id, Monto=monto, IdUsuario=usuario.Id)
    db.session.add(gasto)
    db.session.commit()
    enviarMensaje(chat_id, f"✅ Gasto de ${monto} en '{categoria_nombre}' registrado.")

def gastos(usuario, chat_id):
    lista = (
        Gasto.query
        .filter_by(IdUsuario=usuario.Id)
        .order_by(Gasto.Fecha.desc())
        .limit(10)
        .all()
    )

    if not lista:
        enviarMensaje(chat_id, "No tenés gastos registrados 😪")
        return

    texto = "Últimos gastos:\n\n"
    total = 0
    for g in lista:
        texto += f"• {g.Fecha.strftime('%d/%m %H:%M')} — {g.categoria.Nombre}: ${g.Monto}\n"
        total += g.Monto

    texto += f"\nTotal: ${total:.2f}"
    enviarMensaje(chat_id, texto)

def categorias(usuario, chat_id):
    lista = Categoria.query.filter_by(IdUsuario=usuario.Id).order_by(Categoria.Nombre).all()

    if not lista:
        enviarMensaje(chat_id, "No tenés categorías creadas 😪")
        return

    texto = "🗒️ Tus categorías:\n\n"
    for c in lista:
        texto += f"• {c.Nombre}\n"
    enviarMensaje(chat_id, texto)

def baja(usuario, chat_id):
    usuario.FechaBaja = datetime.now()
    db.session.commit()
    enviarMensaje(chat_id, "Lamentamos que te vayas 😢. Si cambias de opinión, siempre podés volver a escribir /start")

def generarLinkDashboard(usuario):
    link = f"{GRAFANA_URL}/d/{GRAFANA_DASHBOARD_ID}/gastos?var-Usuario={usuario.IdChat}&kiosk=tv"
    usuario.LinkDashboard = link
    db.session.commit()
    return link

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json

    if "message" not in data or "text" not in data["message"]:
        return jsonify({}), 200

    chat_id = data["message"]["chat"]["id"]
    nombre = data["message"]["chat"].get("first_name", "Sin nombre")
    texto = data["message"]["text"].strip().lower()

    usuario = getUsuario(chat_id, nombre)
    
    if not usuario:
        usuario = nuevoUsuario(chat_id, nombre)
    elif usuario.FechaBaja is not None and not texto.startswith("/start"):
        enviarMensaje(chat_id, "Diste de baja nuestro bot 😭. Si querés volver a usarlo, simplemente escribe /start")
        return jsonify({}), 200

    if texto.startswith("/start"):
        generarLinkDashboard(usuario)
        enviarMensaje(chat_id, 
        f"¡Hola {nombre}! 👋\n\n"
        "Bienvenido a MisGastos, tu asistente personal de finanzas 💸\n\n"
        "Desde acá podés registrar tus gastos fácilmente:\n\n"
        "/gasto 100.50 comida — registrar un gasto\n"
        "/gastos — ver tus últimos gastos\n"
        "/categorias — ver tus categorías\n\n"
        "/midashboard — ver un dashboard con tus gastos\n\n"
        "/baja — para dejar de usar el bot\n\n"
        "Para crear una nueva categoría, simplemente usala al registrar un gasto. Si la categoría no existe, se creará automáticamente!\n\n"
        "¡Empecemos a ordenar tus finanzas! 🚀"
    )
    elif texto.startswith("/gasto "):
        args = texto[len("/gasto "):].strip()
        nuevoGasto(usuario, chat_id, args)
    elif texto.startswith("/gastos"):
        gastos(usuario, chat_id)
    elif texto.startswith("/categorias"):
        categorias(usuario, chat_id)
    elif texto.startswith("/baja"):
        baja(usuario, chat_id)
    elif texto.startswith("/midashboard"):
        if not usuario.LinkDashboard:
            generarLinkDashboard(usuario)
        enviarMensaje(chat_id, f'📊 <a href="{usuario.LinkDashboard}">Ver mi dashboard</a>', parse_mode="HTML")
    else:
        enviarMensaje(chat_id, "No pude entender el mensaje 🧐\nTe dejo los comandos disponibles:\n/gasto Ejemplo: 100.50 comida\n/gastos\n/categorias")

    return jsonify({}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)

#TO-DO
# - Agregar comando /categorias para listar categorías del usuario  -- OK
# - Mejorar manejo de errores y validación de comandos
# - Agregar comando /resumen para mostrar resumen mensual de gastos por categoría
# - Validar montos y duplicados -- OK
# - Validar que no se repitan categorias para 1 mismo usuario o que no sean similares o con nombres vacios --OK
# - Agregar comando /eliminar para eliminar un gasto por ID o fecha