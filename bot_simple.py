import os
import json
import random
import requests
from datetime import datetime

# --- CONFIGURACIÓN ---
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")  # Tu chat personal (8852413391)
CHANNEL_ID = "@ViajesIncomparablesOfertas"  # Canal público

WHATSAPP_URL = "https://wa.me/528125644653"

# --- DESTINOS Y PAQUETES DE RESPALDO ---
# Se usan si el scraper no tiene datos recientes
PAQUETES_RESPALDO = [
    {
        "destino": "Cancún",
        "hotel": "Grand Oasis Palm",
        "estrellas": "⭐⭐⭐⭐⭐",
        "noches": 3,
        "precio": 25288,
        "emoji": "🌴"
    },
    {
        "destino": "Riviera Maya",
        "hotel": "Senses Riviera Maya",
        "estrellas": "⭐⭐⭐⭐⭐",
        "noches": 3,
        "precio": 28500,
        "emoji": "🏖️"
    },
    {
        "destino": "Puerto Vallarta",
        "hotel": "Plaza Pelicanos",
        "estrellas": "⭐⭐⭐⭐",
        "noches": 3,
        "precio": 20273,
        "emoji": "🌊"
    },
    {
        "destino": "Los Cabos",
        "hotel": "Riu Santa Fe",
        "estrellas": "⭐⭐⭐⭐⭐",
        "noches": 3,
        "precio": 23787,
        "emoji": "🐠"
    },
    {
        "destino": "Punta Cana",
        "hotel": "Caribe Deluxe Princess",
        "estrellas": "⭐⭐⭐⭐⭐",
        "noches": 4,
        "precio": 36900,
        "emoji": "✈️"
    },
    {
        "destino": "Cozumel",
        "hotel": "Hotel Todo Incluido",
        "estrellas": "⭐⭐⭐⭐",
        "noches": 3,
        "precio": 35515,
        "emoji": "🤿"
    },
]

def cargar_precios_scraper():
    """Intenta cargar precios del archivo generado por el scraper"""
    try:
        if os.path.exists("precios_competencia.json"):
            with open("precios_competencia.json", "r", encoding="utf-8") as f:
                data = json.load(f)
                return data
    except Exception as e:
        print(f"No se encontraron precios del scraper: {e}")
    return None

def generar_mensaje(paquete, precio_competencia=None):
    """Genera el mensaje promocional"""
    
    precio = paquete["precio"]
    destino = paquete["destino"]
    hotel = paquete["hotel"]
    noches = paquete["noches"]
    estrellas = paquete["estrellas"]
    emoji = paquete["emoji"]
    dias = noches + 1

    # Si tenemos precio de la competencia, lo mencionamos
    ahorro_texto = ""
    if precio_competencia and precio_competencia > precio:
        ahorro = precio_competencia - precio
        ahorro_texto = f"\n💰 *Ahorra hasta ${ahorro:,} MXN vs la competencia*"

    hora = datetime.now().strftime("%H:%M")
    
    mensaje = f"""
{emoji} *¡OFERTA VIAJES INCOMPARABLES!* {emoji}

🏨 *{hotel}*
📍 {destino} · {estrellas}
🌙 {dias} días / {noches} noches · 2 adultos

✅ Vuelo directo MTY → {destino.upper()[:3]}
✅ Hotel All Inclusive
✅ Traslado aeropuerto-hotel
✅ Todo incluido{ahorro_texto}

💵 *DESDE MXN$ {precio:,}*
_por paquete completo · 2 personas_

📅 ¿Cuál es tu fecha disponible?
👇 Escríbenos y te cotizamos al momento

📲 [WHATSAPP]({WHATSAPP_URL})

_Viajes Incomparables · Monterrey_
_Actualizado: {hora} hrs_
"""
    return mensaje.strip()

def enviar_mensaje(chat_id, mensaje):
    """Envía mensaje a Telegram"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": mensaje,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True
    }
    try:
        response = requests.post(url, json=payload, timeout=15)
        result = response.json()
        if result.get("ok"):
            print(f"✅ Mensaje enviado a {chat_id}")
            return True
        else:
            print(f"❌ Error enviando a {chat_id}: {result}")
            return False
    except Exception as e:
        print(f"❌ Excepción enviando a {chat_id}: {e}")
        return False

def main():
    print(f"🤖 Bot iniciando - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    if not BOT_TOKEN:
        print("❌ ERROR: TELEGRAM_BOT_TOKEN no configurado")
        return
    
    # Cargar precios del scraper si existen
    datos_scraper = cargar_precios_scraper()
    
    # Elegir paquete aleatorio para variar el contenido
    paquete = random.choice(PAQUETES_RESPALDO)
    
    # Buscar si el scraper tiene datos para este destino
    precio_competencia = None
    if datos_scraper:
        for item in datos_scraper:
            if paquete["destino"].lower() in str(item).lower():
                try:
                    precio_competencia = int(item.get("precio", 0))
                except:
                    pass
                break
    
    # Generar mensaje
    mensaje = generar_mensaje(paquete, precio_competencia)
    
    # Enviar a tu chat personal (como respaldo)
    if CHAT_ID:
        enviar_mensaje(CHAT_ID, mensaje)
    
    # Enviar al canal público
    enviar_mensaje(CHANNEL_ID, mensaje)
    
    print("✅ Bot finalizado correctamente")

if __name__ == "__main__":
    main()
