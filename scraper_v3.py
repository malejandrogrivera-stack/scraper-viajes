import requests
import time
import schedule
from datetime import datetime
import sys
TELEGRAM_TOKEN = "8849301784:AAEnXUZZdbn1AbriAD0qaUmn4D_YD_gSR8g"
TELEGRAM_CHAT_ID = "8852413391"
def enviar_telegram(mensaje):
url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
data = {"chat_id": TELEGRAM_CHAT_ID, "text": mensaje, "parse_mode": "HTML"}
try:
r = requests.post(url, data=data, timeout=10)
print(f"Telegram: {r.status_code} - {r.text}", flush=True)
except Exception as e:
print(f"Error: {e}", flush=True)
def reporte_diario():
ahora = datetime.now().strftime("%d/%m/%Y %H:%M")
mensaje = f"✈️ Viajes Incomparables\n📅 {ahora}\n🏖️ Cancún, Punta Cana, Los Cabos, Cozumel\n📲 wa.me/528125644653"
print(f"Enviando: {ahora}", flush=True)
enviar_telegram(men…
