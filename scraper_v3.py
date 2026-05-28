
import requests
import time
import schedule
from datetime import datetime

# CONFIGURACIÓN
TELEGRAM_TOKEN = "8849301784:AAEnXUZZdbn1AbriAD0qaUmn4D_YD_gSR8g"
TELEGRAM_CHAT_ID = "8852413391"

DESTINOS = [
    {"codigo": "CUN", "nombre": "Cancún"},
    {"codigo": "PUJ", "nombre": "Punta Cana"},
    {"codigo": "SJD", "nombre": "Los Cabos"},
    {"codigo": "CZM", "nombre": "Cozumel"},
]

def enviar_telegram(mensaje):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": mensaje,
        "parse_mode": "HTML"
    }
    try:
        r = requests.post(url, data=data, timeout=10)
        print(f"Telegram: {r.status_code}")
    except Exception as e:
        print(f"Error Telegram: {e}")

def reporte_diario():
    ahora = datetime.now().strftime("%d/%m/%Y %H:%M")
    mensaje = f"""✈️ <b>Viajes Incomparables</b>
📅 Reporte: {ahora}

🏖️ Destinos activos:
* Cancún (CUN)
* Punta Cana (PUJ)
* Los Cabos (SJD)
* Cozumel (CZM)

📲 Para cotizar: wa.me/528125644653
🌐 viajesincomparables.com"""
    enviar_telegram(mensaje)
    print(f"Reporte enviado: {ahora}")

def main():
    print("🚀 Bot Viajes Incomparables iniciado")
    enviar_telegram("✅ Bot iniciado correctamente - Viajes Incomparables")
    schedule.every(6).hours.do(reporte_diario)
    reporte_diario()
    while True:
        schedule.run_pending()
        time.sleep(60)

if _name_ == "_main_":
    main()
