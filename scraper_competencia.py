# -*- coding: utf-8 -*-
# Scraper de competencia v2 - Viajes Incomparables
# Ahora con DETALLE por oferta: hotel, noches, fechas, vuelo y precio
# para que puedas comparar y armar tus flyers.

import re
import requests
from datetime import datetime

TOKEN = "8849301784:AAEnXUZZdbn1AbriAD0qaUmn4D_YD_gSR8g"
CHAT_ID = "8852413391"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept-Language": "es-MX,es;q=0.9",
}

BASE = "https://travelviajes.com.mx/vuelo-hotel/monterrey/"
RUTAS = [
    ("Cancún", BASE + "cancun"),
    ("Los Cabos", BASE + "los-cabos"),
    ("Puerto Vallarta", BASE + "puerto-vallarta"),
    ("Mazatlán", BASE + "mazatlan"),
    ("Huatulco", BASE + "huatulco"),
    ("Acapulco", BASE + "acapulco"),
    ("Oaxaca", BASE + "oaxaca"),
    ("Orlando", BASE + "orlando"),
    ("Punta Cana", BASE + "punta-cana"),
    ("CDMX", BASE + "ciudad-de-mexico"),
    ("Guadalajara", BASE + "guadalajara"),
]


def limpiar_html(html):
    """Quita etiquetas y deja solo texto plano."""
    texto = re.sub(r"<script.*?</script>", " ", html, flags=re.S | re.I)
    texto = re.sub(r"<style.*?</style>", " ", texto, flags=re.S | re.I)
    texto = re.sub(r"<[^>]+>", " ", texto)
    texto = re.sub(r"&aacute;", "á", texto)
    texto = re.sub(r"&eacute;", "é", texto)
    texto = re.sub(r"&iacute;", "í", texto)
    texto = re.sub(r"&oacute;", "ó", texto)
    texto = re.sub(r"&uacute;", "ú", texto)
    texto = re.sub(r"&ntilde;", "ñ", texto)
    texto = re.sub(r"\s+", " ", texto)
    return texto


def extraer_ofertas(texto):
    """Saca cada oferta: días/noches, hotel, vuelo, fechas y precio."""
    patron = re.compile(
        r"Paquete\s+(\d+)\s+D[ÍI]AS\s*/\s*(\d+)\s+NOCHES\s+(.{3,80}?)\s+Partiendo desde \w+"
        r"(.{0,600}?)Desde\s+([\d,]+)\s+MXN",
        re.I,
    )
    ofertas = []
    for m in patron.finditer(texto):
        dias, noches, hotel, detalle, precio = m.groups()
        vuelo = "directo" if re.search(r"Vuelo directo", detalle, re.I) else "con escalas"
        fechas = re.search(r"Desde:\s*(\w{3}\s+\d{1,2}\s+\w{3}).{0,40}?Hasta:\s*(\w{3}\s+\d{1,2}\s+\w{3})", detalle)
        salida = fechas.group(1) if fechas else "?"
        regreso = fechas.group(2) if fechas else "?"
        try:
            valor = int(precio.replace(",", ""))
        except ValueError:
            continue
        ofertas.append({
            "hotel": hotel.strip(),
            "dias": dias,
            "noches": noches,
            "vuelo": vuelo,
            "salida": salida,
            "regreso": regreso,
            "precio": valor,
        })
    # Ordenar por precio y quitar duplicados exactos
    unicas = []
    vistas = set()
    for o in sorted(ofertas, key=lambda x: x["precio"]):
        clave = (o["hotel"], o["precio"], o["salida"])
        if clave not in vistas:
            vistas.add(clave)
            unicas.append(o)
    return unicas


def revisar_ruta(destino, url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=30)
        if r.status_code != 200:
            return []  # ruta no existe para MTY, se omite
        ofertas = extraer_ofertas(limpiar_html(r.text))
        if not ofertas:
            return []  # sin ofertas hoy, se omite
        lineas = [f"📍 {destino.upper()} ({len(ofertas)} ofertas)"]
        for o in ofertas[:3]:  # Top 3 más baratas por destino
            lineas.append(
                f"  🏨 {o['hotel']}\n"
                f"  🌙 {o['dias']}D/{o['noches']}N · ✈️ {o['vuelo']}\n"
                f"  📅 {o['salida']} → {o['regreso']}\n"
                f"  💰 ${o['precio']:,} MXN p/persona"
            )
        return lineas
    except Exception as e:
        return [f"❌ {destino}: error ({type(e).__name__})"]


def enviar(mensaje):
    # Telegram limita a 4096 caracteres: dividir en partes si es necesario
    while mensaje:
        parte = mensaje[:4000]
        if len(mensaje) > 4000:
            corte = parte.rfind("\n\n")
            if corte > 0:
                parte = mensaje[:corte]
        requests.post(
            f"https://api.telegram.org/bot{TOKEN}/sendMessage",
            data={"chat_id": CHAT_ID, "text": parte},
            timeout=30,
        )
        mensaje = mensaje[len(parte):].lstrip()


def main():
    fecha = datetime.now().strftime("%d/%m/%Y %H:%M")
    lineas = ["🕵️ COMPETENCIA · Travel Viajes MTY", f"📅 {fecha}", ""]
    for destino, url in RUTAS:
        resultado = revisar_ruta(destino, url)
        if resultado:
            lineas += resultado
            lineas.append("")
    lineas += ["✈️ Viajes Incomparables"]
    enviar("\n".join(lineas))
    print("\n".join(lineas))


if __name__ == "__main__":
    main()
