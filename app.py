from flask import Flask, request, jsonify
from dotenv import load_dotenv
import mysql.connector
import requests
import os

load_dotenv()

app = Flask(__name__)

TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_API = f"https://api.telegram.org/bot{TOKEN}"

def get_db():
    return mysql.connector.connect(
        host=os.getenv("MYSQL_HOST"),
        user=os.getenv("MYSQL_USER"),
        password=os.getenv("MYSQL_PASSWORD"),
        database=os.getenv("MYSQL_DATABASE")
    )

def enviarMensaje(chat_id, texto):
    requests.post(f"{TELEGRAM_API}/sendMessage", json={
        "chat_id": chat_id,
        "text": texto
    })

def getCategoria(cursor, nombre, id_usuario):
    cursor.execute(
        "SELECT Id FROM Categorias WHERE Nombre = %s AND IdUsuario = %s",
        (nombre, id_usuario)
    )
    result = cursor.fetchone()
    if result:
        return result[0]
    cursor.execute(
        "INSERT INTO Categorias (Nombre, IdUsuario) VALUES (%s, %s)",
        (nombre, id_usuario)
    )
    return cursor.lastrowid

def nuevoGasto(cursor, id_usuario, chat_id, args):
    # Formato esperado: /gasto 100.50 comida
    try:
        partes = args.split(" ", 1)
        monto = float(partes[0])
        categoria_nombre = partes[1].strip().lower()
    except:
        enviarMensaje(chat_id, "⚠️ Formato incorrecto. Usá: /gasto 100.50 comida")
        return

    id_categoria = getCategoria(cursor, categoria_nombre, id_usuario)
    cursor.execute(
        "INSERT INTO Gastos (IdCategoria, Monto, IdUsuario) VALUES (%s, %s, %s)",
        (id_categoria, monto, id_usuario)
    )
    enviarMensaje(chat_id, f"✅ Gasto de ${monto} en '{categoria_nombre}' registrado.")

def handle_gastos(cursor, id_usuario, chat_id):
    cursor.execute("""
        SELECT c.Nombre, g.Monto, g.Fecha
        FROM Gastos g
        JOIN Categorias c ON g.IdCategoria = c.Id
        WHERE g.IdUsuario = %s
        ORDER BY g.Fecha DESC
        LIMIT 10
    """, (id_usuario,))
    gastos = cursor.fetchall()

    if not gastos:
        enviarMensaje(chat_id, "No tenés gastos registrados.")
        return

    texto = "Últimos gastos:\n\n"
    for g in gastos:
        texto += f"• {g[2].strftime('%d/%m')} — {g[0]}: ${g[1]}\n"
    enviarMensaje(chat_id, texto)

def handle_categorias(cursor, id_usuario, chat_id):
    cursor.execute(
        "SELECT Nombre FROM Categorias WHERE IdUsuario = %s ORDER BY Nombre",
        (id_usuario,)
    )
    categorias = cursor.fetchall()

    if not categorias:
        enviarMensaje(chat_id, "No tenés categorías creadas.")
        return

    texto = "Tus categorías:\n\n"
    for c in categorias:
        texto += f"• {c[0]}\n"
    enviarMensaje(chat_id, texto)

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json

    # Ignorar si no es un mensaje de texto
    if "message" not in data or "text" not in data["message"]:
        return jsonify({}), 200

    chat_id = data["message"]["chat"]["id"]
    texto = data["message"]["text"].strip()

    db = get_db()
    cursor = db.cursor()

    # Buscar o crear usuario
    cursor.execute("SELECT Id FROM Usuario WHERE IdChat = %s", (chat_id,))
    usuario = cursor.fetchone()
    if not usuario:
        cursor.execute(
            "INSERT INTO Usuario (IdChat, IdTipo, Nombre) VALUES (%s, %s, %s)",
            (chat_id, 1, data["message"]["chat"].get("first_name", "Sin nombre"))
        )
        db.commit()
        cursor.execute("SELECT Id FROM Usuario WHERE IdChat = %s", (chat_id,))
        usuario = cursor.fetchone()

    id_usuario = usuario[0]

    # Parsear comando
    if texto.startswith("/gasto "):
        args = texto[len("/gasto "):].strip()
        nuevoGasto(cursor, id_usuario, chat_id, args)
    elif texto.startswith("/gastos"):
        handle_gastos(cursor, id_usuario, chat_id)
    elif texto.startswith("/categorias"):
        handle_categorias(cursor, id_usuario, chat_id)
    else:
        enviarMensaje(chat_id, "Comandos disponibles:\n/gasto 100.50 comida\n/gastos\n/categorias")

    db.commit()
    db.close()

    return jsonify({}), 200

if __name__ == "__main__":
    app.run(debug=True)



#TO-DO
# - Agregar comando /categorias para listar categorías del usuario
# - Mejorar manejo de errores y validación de comandos
# - Agregar comando /resumen para mostrar resumen mensual de gastos por categoría
# - Validar montos y duplicados
# - Validar que no se repitan categorias para 1 mismo usuario o que no sean similares o con nombres vacios
# - Agregar comando /eliminar para eliminar un gasto por ID o fecha
