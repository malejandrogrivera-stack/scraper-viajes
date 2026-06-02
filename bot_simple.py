import requests
from datetime import datetime
TOKEN = "8849301784:AAEnXUZZdbn1AbriAD0qaUmn4D_YD_gSR8g"
CHAT_ID = "8852413391"
ahora = datetime.now().strftime("%d/%m/%Y %H:%M")
msg = f"✈️ Viajes Incomparables\n📅 {ahora}\n🏖️ Cancún, Punta Cana, Los Cabos\n📲 wa.me/528125644653"
r = requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", data={"chat_id": CHAT_ID, "text": msg})
print(f"Enviado: {r.status_code}")
