# -*- coding: utf-8 -*-
# Scraper de competencia - Viajes Incomparables
# Monitorea: Travel Viajes MTY, Mega Travel, PriceTravel
# Corre en GitHub Actions y manda resumen a Telegram

import re
import requests
from datetime import datetime

TOKEN = "8849301784:AAEnXUZZdbn1AbriAD0qaUmn4D_YD_gSR8g"
CHAT_ID = "8852413391"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept-Language": "es-MX,es;q=0.9",
}


def extraer_precios(texto):
    """Encuentra precios tipo $5,998 o MXN$22,742 en el texto de la pagina."""
    precios = re.findall(r"\$\s?([\d]{1,3}(?:,\d{3})+|\d{4,6})(?:\.\d{2})?", texto)
    limpios = []
    for p in precios:
        try:
            valor = int(p.replace(",", ""))
            # Filtrar precios razonables de paquetes (entre 3 mil y 200 mil)
            if 3000 <= valor <= 200000:
                limpios.append(valor)
        except ValueError:
            pass
    return sorted(set(limpios))


def revisar(nombre, url):
    """Descarga una pagina y regresa resumen de precios encontrados."""
    try:
        r = requests.get(url, headers=HEADERS, timeout=30)
        if r.status_code != 200:
            return f"⚠️ {nombre}: no respondió (código {r.status_code})"
        precios = extraer_precios(r.text)
        if not precios:
            return f"➖ {nombre}: sin precios visibles hoy"
        minimo = f"{precios[0]:,}"
        maximo = f"{precios[-1]:,}"
        if len(precios) == 1:
            return f"💰 {nombre}: desde ${minimo} MXN"
        return f"💰 {nombre}: desde ${minimo} hasta ${maximo} MXN ({len(precios)} precios)"
    except Exception as e:
        return f"❌ {nombre}: error ({type(e).__name__})"


def main():
    fuentes = [
        ("Travel Viajes MTY · Cancún", "https://travelviajes.com.mx/vuelo-hotel/monterrey/cancun"),
        ("Travel Viajes MTY · Paquetes", "https://travelviajesmonterrey.com/paquetes-de-viajes-todo-incluido"),
        ("Mega Travel · desde MTY", "https://megatravel.tviajes.com/viajes-desde-monterrey"),
        ("PriceTravel · Cancún", "https://www.pricetravel.com/paquetes-a-cancun"),
    ]

    fecha = datetime.now().strftime("%d/%m/%Y %H:%M")
    lineas = [f"🕵️ MONITOREO DE COMPETENCIA", f"📅 {fecha}", ""]

    for nombre, url in fuentes:
        lineas.append(revisar(nombre, url))

    lineas += ["", "✈️ Viajes Incomparables", "📲 wa.me/528125644653"]
    mensaje = "\n".join(lineas)

    requests.post(
        f"https://api.telegram.org/bot{TOKEN}/sendMessage",
        data={"chat_id": CHAT_ID, "text": mensaje},
        timeout=30,
    )
    print(mensaje)


if __name__ == "__main__":
    main()
