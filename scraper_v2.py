"""
╔══════════════════════════════════════════════════════════════════╗
║   SCRAPER DESPEGAR — Viajes Incomparables                        ║
║   Rastreo de paquetes (vuelo + hotel) desde MTY                  ║
║   → Alerta WhatsApp si baja precio                               ║
║   → Flyer HTML automático DIARIO                                 ║
╚══════════════════════════════════════════════════════════════════╝
"""

import json, os, time, schedule, requests
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

# ──────────────────────────────────────────────────────────
# CONFIGURACIÓN — edita con tus datos
# ──────────────────────────────────────────────────────────
WHATSAPP_TOKEN = "TU_TOKEN_AQUI"
WHATSAPP_PHONE = "521XXXXXXXXXX"   # tu número de negocio
WHATSAPP_TO    = "521XXXXXXXXXX"   # número que recibe alertas

ADULTOS        = 2
NOCHES         = 3
PRECIO_MAXIMO  = 45000             # alerta si está por debajo (MXN)
ARCHIVO_PRECIOS = "precios_anteriores.json"

# ──────────────────────────────────────────────────────────
# DESTINOS COMPLETOS
# ──────────────────────────────────────────────────────────
DESTINOS = [
    # ── México Caribe
    {"codigo": "CUN",  "nombre": "Cancún",           "emoji": "🌴", "zona": "México Caribe"},
    {"codigo": "PCM",  "nombre": "Playa del Carmen",  "emoji": "🏖️", "zona": "México Caribe"},
    {"codigo": "CZM",  "nombre": "Cozumel",           "emoji": "🤿", "zona": "México Caribe"},
    {"codigo": "MID",  "nombre": "Costa Mujeres",     "emoji": "🐠", "zona": "México Caribe"},
    {"codigo": "MRD",  "nombre": "Mérida",             "emoji": "🏛️", "zona": "México Caribe"},

    # ── México Pacífico
    {"codigo": "PVR",  "nombre": "Puerto Vallarta",   "emoji": "🌺", "zona": "México Pacífico"},
    {"codigo": "MZT",  "nombre": "Mazatlán",           "emoji": "🦐", "zona": "México Pacífico"},
    {"codigo": "ACA",  "nombre": "Acapulco",           "emoji": "🌊", "zona": "México Pacífico"},
    {"codigo": "SJD",  "nombre": "Los Cabos",          "emoji": "🐋", "zona": "México Pacífico"},

    # ── Colombia
    {"codigo": "MDE",  "nombre": "Medellín",           "emoji": "🌸", "zona": "Colombia"},
    {"codigo": "BOG",  "nombre": "Bogotá",             "emoji": "☕", "zona": "Colombia"},
    {"codigo": "CTG",  "nombre": "Cartagena",          "emoji": "🏰", "zona": "Colombia"},

    # ── EUA
    {"codigo": "MCO",  "nombre": "Orlando",            "emoji": "🎢", "zona": "EUA"},

    # ── Europa
    {"codigo": "CDG",  "nombre": "París",              "emoji": "🗼", "zona": "Europa"},
    {"codigo": "FCO",  "nombre": "Roma",               "emoji": "🏟️", "zona": "Europa"},
    {"codigo": "BCN",  "nombre": "Barcelona",          "emoji": "🥘", "zona": "Europa"},
]

# Códigos adicionales que se buscan agrupados con su destino principal
DESTINOS_AGRUPADOS = {
    "CUN": ["CUN", "PCM", "CZM"],   # Cancún + Riviera Maya + Cozumel
    "PVR": ["PVR", "MZT"],           # Vallarta + Riviera Nayarit
}

# ──────────────────────────────────────────────────────────
# 1. SCRAPING
# ──────────────────────────────────────────────────────────
def url_busqueda(codigo):
    fecha_sal = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
    fecha_reg = (datetime.now() + timedelta(days=30 + NOCHES)).strftime("%Y-%m-%d")
    return (
        f"https://www.despegar.com.mx/packages/results"
        f"?origin=MTY&destination={codigo}"
        f"&departureDate={fecha_sal}&returnDate={fecha_reg}"
        f"&adults={ADULTOS}&children=0&infants=0"
    )

def raspar_precio(destino):
    codigo = destino["codigo"]
    nombre = destino["nombre"]
    print(f"  🔍 MTY → {nombre} ({codigo})...")
    url = url_busqueda(codigo)

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page    = browser.new_page()
            page.set_extra_http_headers({
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
                )
            })
            page.goto(url, timeout=60000)
            page.wait_for_timeout(6000)
            html = page.content()
            browser.close()

        soup    = BeautifulSoup(html, "html.parser")
        precios = []
        for tag in soup.find_all(True):
            texto = tag.get_text(strip=True)
            if ("$" in texto or "MXN" in texto) and any(c.isdigit() for c in texto):
                limpio = ''.join(filter(str.isdigit, texto.replace(",", "")))
                if limpio:
                    valor = int(limpio[:7])
                    if 3000 < valor < 500000:
                        precios.append(valor)

        precio_min = min(precios) if precios else None
    except Exception as e:
        print(f"    ⚠️ Error: {e}")
        precio_min = None

    return {
        **destino,
        "precio":       precio_min,
        "precio_fmt":   f"MXN${precio_min:,}" if precio_min else "N/D",
        "fecha_salida": (datetime.now() + timedelta(days=30)).strftime("%d/%m/%Y"),
        "url":          url,
        "timestamp":    datetime.now().strftime("%Y-%m-%d %H:%M"),
    }

# ──────────────────────────────────────────────────────────
# 2. HISTORIAL Y DETECCIÓN DE BAJADAS
# ──────────────────────────────────────────────────────────
def cargar_anteriores():
    if os.path.exists(ARCHIVO_PRECIOS):
        with open(ARCHIVO_PRECIOS) as f:
            return json.load(f)
    return {}

def guardar(datos):
    with open(ARCHIVO_PRECIOS, "w") as f:
        json.dump({d["codigo"]: d for d in datos}, f, indent=2, ensure_ascii=False)

def bajada_significativa(codigo, precio_nuevo, anteriores):
    if codigo not in anteriores or not precio_nuevo:
        return False, 0
    viejo = anteriores[codigo].get("precio")
    if not viejo:
        return False, 0
    pct = (viejo - precio_nuevo) / viejo * 100
    return pct >= 5, round(pct, 1)

# ──────────────────────────────────────────────────────────
# 3. WHATSAPP
# ──────────────────────────────────────────────────────────
def enviar_whatsapp(mensaje):
    if WHATSAPP_TOKEN == "TU_TOKEN_AQUI":
        print(f"  [WhatsApp no configurado]\n{mensaje}\n")
        return
    url = f"https://graph.facebook.com/v18.0/{WHATSAPP_PHONE}/messages"
    r = requests.post(url,
        headers={"Authorization": f"Bearer {WHATSAPP_TOKEN}", "Content-Type": "application/json"},
        json={"messaging_product": "whatsapp", "to": WHATSAPP_TO,
              "type": "text", "text": {"body": mensaje}}
    )
    estado = "✅ Enviado" if r.status_code == 200 else f"❌ Error {r.status_code}"
    print(f"  WhatsApp: {estado}")

def msg_alerta(r, precio_viejo=None, pct=0):
    lineas = [
        f"🔥 *¡PRECIO BAJO!* {r['emoji']} MTY → {r['nombre']}",
        f"💰 {r['precio_fmt']} · {ADULTOS} adultos · {NOCHES} noches",
        f"📅 Salida aprox.: {r['fecha_salida']}",
    ]
    if precio_viejo:
        lineas.append(f"📉 Bajó {pct}% (antes MXN${precio_viejo:,})")
    lineas += [f"🔗 {r['url']}", f"_Viajes Incomparables · {r['timestamp']}_"]
    return "\n".join(lineas)

# ──────────────────────────────────────────────────────────
# 4. FLYER DIARIO
# ──────────────────────────────────────────────────────────
def generar_flyer_diario(resultados):
    fecha_hoy = datetime.now().strftime("%d de %B %Y")
    dia_semana = datetime.now().strftime("%A").upper()

    # Agrupar por zona
    zonas = {}
    for r in resultados:
        z = r["zona"]
        zonas.setdefault(z, []).append(r)

    secciones_html = ""
    for zona, items in zonas.items():
        iconos = {"México Caribe": "🌴", "México Pacífico": "🌊",
                  "Colombia": "🌸", "EUA": "🎢", "Europa": "🗼"}
        secciones_html += f"""
        <div class="zona-header">
          <span>{iconos.get(zona,'✈️')}</span> {zona}
        </div>"""
        for r in items:
            color = "#f0a500" if r.get("precio") and r["precio"] < PRECIO_MAXIMO else "#00c8ff"
            badge = "🔥 HOT" if r.get("precio") and r["precio"] < PRECIO_MAXIMO else ""
            secciones_html += f"""
        <div class="dest-row">
          <div class="dest-left">
            <div class="dest-name">{r['emoji']} {r['nombre']}</div>
            <div class="dest-sub">MTY · {NOCHES} noches · {ADULTOS} adultos · salida {r['fecha_salida']}</div>
          </div>
          <div class="dest-right">
            <div class="dest-price" style="color:{color}">{r['precio_fmt']}</div>
            <div class="dest-badge">{badge}</div>
          </div>
        </div>"""

    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<link href="https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Montserrat:wght@500;600;700;800;900&display=swap" rel="stylesheet">
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ background:#0d0d1a; display:flex; justify-content:center; padding:20px; font-family:'Montserrat',sans-serif; }}
  .flyer {{ width:480px; background:linear-gradient(160deg,#0a1628,#0d2137,#061020); border-radius:20px; overflow:hidden; box-shadow:0 30px 80px rgba(0,0,0,0.8); }}

  /* Header */
  .header {{ background:rgba(255,255,255,0.04); padding:16px 22px; border-bottom:1px solid rgba(255,255,255,0.08); display:flex; justify-content:space-between; align-items:center; }}
  .logo-row {{ display:flex; align-items:center; gap:10px; }}
  .logo-circle {{ width:52px; height:52px; border-radius:50%; background:linear-gradient(135deg,#3a7bd5,#8b6914); display:flex; align-items:center; justify-content:center; font-size:22px; border:2px solid rgba(255,255,255,0.2); }}
  .brand {{ font-size:13px; font-weight:800; color:#fff; text-transform:uppercase; }}
  .sub {{ font-size:8px; font-weight:600; color:#f0a500; letter-spacing:2px; text-transform:uppercase; }}
  .dia-badge {{ background:linear-gradient(135deg,#1a3a6a,#0d5ca8); color:#fff; padding:7px 14px; border-radius:20px; font-size:10px; font-weight:800; letter-spacing:1px; border:1px solid rgba(255,255,255,0.15); }}

  /* Título */
  .titulo {{ padding:18px 22px 10px; text-align:center; }}
  .t1 {{ font-size:10px; font-weight:700; color:#f0a500; letter-spacing:2px; text-transform:uppercase; margin-bottom:3px; }}
  .t2 {{ font-family:'Bebas Neue',sans-serif; font-size:40px; color:#fff; line-height:1; }}
  .t2 span {{ color:#00c8ff; }}
  .t3 {{ font-size:10px; color:rgba(255,255,255,0.4); margin-top:4px; }}

  /* Destinos */
  .destinos {{ padding:6px 22px 16px; }}
  .zona-header {{
    font-size:10px; font-weight:800; color:#f0a500;
    letter-spacing:2px; text-transform:uppercase;
    padding:12px 0 6px; border-top:1px solid rgba(255,255,255,0.06);
    display:flex; align-items:center; gap:6px;
  }}
  .dest-row {{
    display:flex; justify-content:space-between; align-items:center;
    background:rgba(255,255,255,0.04); border:1px solid rgba(255,255,255,0.07);
    border-radius:12px; padding:10px 14px; margin-bottom:7px;
  }}
  .dest-name {{ font-size:14px; font-weight:800; color:#fff; margin-bottom:2px; }}
  .dest-sub {{ font-size:9px; color:rgba(255,255,255,0.4); }}
  .dest-price {{ font-family:'Bebas Neue',sans-serif; font-size:28px; line-height:1; text-align:right; }}
  .dest-badge {{ font-size:9px; font-weight:800; color:#ff4444; text-align:right; }}

  /* CTA */
  .cta {{ padding:0 22px 20px; }}
  .cta-btn {{
    width:100%; background:linear-gradient(135deg,#00c853,#00a040);
    color:#fff; border:none; border-radius:14px; padding:15px;
    font-size:13px; font-weight:800; letter-spacing:1px; text-transform:uppercase;
    font-family:'Montserrat',sans-serif; cursor:pointer;
    display:flex; align-items:center; justify-content:center; gap:8px;
    box-shadow:0 6px 20px rgba(0,200,80,0.3);
  }}
  .foot {{ padding:0 22px 16px; text-align:center; font-size:8px; color:rgba(255,255,255,0.2); }}
</style>
</head>
<body>
<div class="flyer">
  <div class="header">
    <div class="logo-row">
      <div class="logo-circle">🌴</div>
      <div><div class="brand">Viajes</div><div class="sub">Incomparables</div></div>
    </div>
    <div class="dia-badge">📊 {dia_semana}</div>
  </div>

  <div class="titulo">
    <div class="t1">Reporte diario de precios</div>
    <div class="t2">Mejores <span>Precios</span> Hoy</div>
    <div class="t3">{fecha_hoy} · Origen MTY · {ADULTOS} adultos · {NOCHES} noches</div>
  </div>

  <div class="destinos">
    {secciones_html}
  </div>

  <div class="cta">
    <button class="cta-btn">
      📲 RESERVA POR WHATSAPP
    </button>
  </div>
  <!-- Sección Viajes Lili en flyer (se llena dinámicamente) -->
  <div id="lili-section"></div>
  <div class="foot">
    Precios obtenidos de Despegar.com.mx · Sujetos a cambios y disponibilidad · Viajes Incomparables © {datetime.now().year}
  </div>
</div>
</body>
</html>"""

    archivo = f"flyer_diario_{datetime.now().strftime('%Y%m%d')}.html"
    with open(archivo, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"  🖼️  Flyer diario generado: {archivo}")
    return archivo



# ──────────────────────────────────────────────────────────
# MÓDULO: VIAJES LILI — Monitor de promociones
# Sitio: lili.tviajes.com
# ──────────────────────────────────────────────────────────

LILI_URL      = "https://lili.tviajes.com"
LILI_ARCHIVO  = "promos_lili.json"

def raspar_viajes_lili():
    """
    Raspa el sitio de Viajes Lili buscando paquetes y precios.
    Retorna lista de promos encontradas.
    """
    print("\n🔍 Revisando Viajes Lili...")
    promos = []

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page    = browser.new_page()
            page.set_extra_http_headers({
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
                )
            })
            page.goto(LILI_URL, timeout=60000)
            page.wait_for_timeout(5000)

            # Intentar hacer clic en sección de paquetes/ofertas si existe
            try:
                page.click("a[href*='paquete'], a[href*='oferta'], a[href*='promo']",
                           timeout=3000)
                page.wait_for_timeout(3000)
            except:
                pass

            html = page.content()
            browser.close()

        soup = BeautifulSoup(html, "html.parser")

        # Buscar bloques de destino/precio
        candidatos = soup.find_all(["div", "article", "section", "li"])
        vistos = set()

        for bloque in candidatos:
            texto = bloque.get_text(" ", strip=True)

            # Filtrar bloques con precio y destino
            tiene_precio   = "$" in texto or "MXN" in texto or "precio" in texto.lower()
            tiene_destino  = any(d in texto for d in [
                "Cancún","Cancun","Vallarta","Cabos","Mazatlán","Mazatlan",
                "Acapulco","Cozumel","Mérida","Merida","Bogotá","Bogota",
                "Medellín","Medellin","Cartagena","Orlando","París","Paris",
                "Roma","Barcelona","Punta Cana","Riviera"
            ])

            if tiene_precio and tiene_destino and len(texto) < 500:
                clave = texto[:80]
                if clave in vistos:
                    continue
                vistos.add(clave)

                # Extraer precio si hay
                precio = None
                for token in texto.replace(",","").split():
                    digitos = ''.join(filter(str.isdigit, token))
                    if digitos and 3000 < int(digitos[:7]) < 500000:
                        precio = int(digitos[:7])
                        break

                promos.append({
                    "agencia":    "Viajes Lili",
                    "texto":      texto[:200],
                    "precio":     precio,
                    "precio_fmt": f"MXN${precio:,}" if precio else "Ver sitio",
                    "url":        LILI_URL,
                    "timestamp":  datetime.now().strftime("%Y-%m-%d %H:%M"),
                })

        print(f"  ✓  Viajes Lili: {len(promos)} promos encontradas")

    except Exception as e:
        print(f"  ❌ Error Viajes Lili: {e}")

    return promos


def cargar_promos_anteriores_lili():
    if os.path.exists(LILI_ARCHIVO):
        with open(LILI_ARCHIVO) as f:
            return json.load(f)
    return []

def guardar_promos_lili(promos):
    with open(LILI_ARCHIVO, "w", encoding="utf-8") as f:
        json.dump(promos, f, indent=2, ensure_ascii=False)

def detectar_promos_nuevas_lili(promos_nuevas, promos_anteriores):
    """Detecta promos que no estaban antes por texto."""
    textos_anteriores = {p["texto"][:80] for p in promos_anteriores}
    nuevas = [p for p in promos_nuevas if p["texto"][:80] not in textos_anteriores]
    return nuevas

def msg_alerta_lili(promo):
    return (
        f"👀 *¡PROMO NUEVA — Viajes Lili!*\n"
        f"📦 {promo['texto'][:150]}\n"
        f"💰 {promo['precio_fmt']}\n"
        f"🔗 {promo['url']}\n"
        f"_Viajes Incomparables · {promo['timestamp']}_"
    )

def revisar_viajes_lili():
    """Tarea principal de monitoreo de Viajes Lili."""
    anteriores = cargar_promos_anteriores_lili()
    nuevas_promos = raspar_viajes_lili()

    if not nuevas_promos:
        return

    # Detectar promos que no existían antes
    recien_aparecidas = detectar_promos_nuevas_lili(nuevas_promos, anteriores)

    if recien_aparecidas:
        print(f"  🔔 {len(recien_aparecidas)} promo(s) NUEVA(S) en Viajes Lili")
        for promo in recien_aparecidas:
            print(f"     → {promo['texto'][:80]}")
            enviar_whatsapp(msg_alerta_lili(promo))
    else:
        print("  ✓  Viajes Lili: sin cambios nuevos")

    guardar_promos_lili(nuevas_promos)
    return nuevas_promos


# ──────────────────────────────────────────────────────────
# 5. TAREA PRINCIPAL
# ──────────────────────────────────────────────────────────
def revisar_precios(generar_flyer=False):
    print(f"\n{'='*55}")
    print(f"🔎 Revisando {len(DESTINOS)} destinos — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*55}")

    anteriores = cargar_anteriores()
    resultados = []

    for destino in DESTINOS:
        try:
            r = raspar_precio(destino)
            resultados.append(r)

            if r["precio"]:
                bajó, pct = bajada_significativa(r["codigo"], r["precio"], anteriores)
                if bajó:
                    viejo = anteriores[r["codigo"]]["precio"]
                    print(f"  📉 ¡Bajó {pct}%! {r['nombre']}: {viejo:,} → {r['precio']:,}")
                    enviar_whatsapp(msg_alerta(r, viejo, pct))
                elif r["precio"] < PRECIO_MAXIMO:
                    print(f"  🔥 {r['nombre']}: {r['precio_fmt']} (bajo del límite)")
                    enviar_whatsapp(msg_alerta(r))
                else:
                    print(f"  ✓  {r['nombre']}: {r['precio_fmt']}")
            else:
                print(f"  ⚠️  {r['nombre']}: sin precio")

            time.sleep(4)
        except Exception as e:
            print(f"  ❌ Error {destino['nombre']}: {e}")

    guardar(resultados)

    # ── Revisar Viajes Lili también
    promos_lili = revisar_viajes_lili()

    if generar_flyer and resultados:
        archivo = generar_flyer_diario(resultados)
        enviar_whatsapp(
            f"📊 *Reporte diario listo — {datetime.now().strftime('%d/%m/%Y')}*\n"
            f"Se revisaron {len(resultados)} destinos desde MTY.\n"
            f"Flyer guardado: {archivo}\n"
            f"_Viajes Incomparables_"
        )

    return resultados

# ──────────────────────────────────────────────────────────
# 6. PROGRAMACIÓN
# ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("🚀 Scraper Viajes Incomparables iniciado")
    print(f"   Destinos: {len(DESTINOS)} ciudades")
    print(f"   Revisión de precios: cada 6 horas")
    print(f"   Flyer diario: todos los días a las 7:00 AM\n")

    # Primera corrida inmediata con flyer
    revisar_precios(generar_flyer=True)

    # Revisión Despegar cada 6 horas
    schedule.every(6).hours.do(revisar_precios, generar_flyer=False)

    # Viajes Lili cada 3 horas (publican promos frecuentemente)
    schedule.every(3).hours.do(revisar_viajes_lili)

    # Flyer diario a las 7 AM
    schedule.every().day.at("07:00").do(revisar_precios, generar_flyer=True)

    print("\n⏳ Corriendo... (Ctrl+C para detener)\n")
    while True:
        schedule.run_pending()
        time.sleep(60)
