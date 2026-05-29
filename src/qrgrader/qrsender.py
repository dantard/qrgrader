"""
Envío masivo de correos personalizados con adjuntos
====================================================
Requisitos:
  pip install pandas

Preparar un CSV con estas columnas:
  nombre, email, texto, fichero

Ejemplo de fila en el CSV:
  Juan García, juan@example.com, "Hola Juan, tu nota es un 8...", /ruta/al/fichero_juan.pdf
"""

import smtplib
import csv
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

# ──────────────────────────────────────────────
# CONFIGURACIÓN — edita estos valores
# ──────────────────────────────────────────────
SMTP_SERVER   = "smtp.gmail.com"        # Gmail. Outlook: smtp.office365.com
SMTP_PORT     = 587
REMITENTE     = "tu_correo@gmail.com"
CONTRASENA    = "ibadwgsoirmfvngs"  # Ver nota al final
ASUNTO        = "Información importante sobre tu evaluación"
CSV_FICHERO   = "alumnos.csv"           # Ruta a tu archivo CSV
# ──────────────────────────────────────────────


def crear_correo(remitente, destinatario, asunto, cuerpo, ruta_adjunto=None):
    """Construye el mensaje MIME con texto y adjunto opcional."""
    msg = MIMEMultipart()
    msg["From"]    = remitente
    msg["To"]      = destinatario
    msg["Subject"] = asunto

    msg.attach(MIMEText(cuerpo, "plain", "utf-8"))

    if ruta_adjunto and os.path.isfile(ruta_adjunto):
        with open(ruta_adjunto, "rb") as f:
            parte = MIMEBase("application", "octet-stream")
            parte.set_payload(f.read())
        encoders.encode_base64(parte)
        nombre_fichero = os.path.basename(ruta_adjunto)
        parte.add_header("Content-Disposition", f'attachment; filename="{nombre_fichero}"')
        msg.attach(parte)
    elif ruta_adjunto:
        print(f"  ⚠️  Adjunto no encontrado: {ruta_adjunto}")

    return msg


def enviar_correos(csv_path):
    enviados  = 0
    fallidos  = 0
    errores   = []

    # Leer CSV
    with open(csv_path, newline="", encoding="utf-8") as f:
        alumnos = list(csv.DictReader(f))

    total = len(alumnos)
    print(f"📋 {total} alumnos cargados. Iniciando envío...\n")

    # Conectar al servidor SMTP una sola vez (más eficiente)
    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as servidor:
        servidor.ehlo()
        servidor.starttls()
        servidor.login(REMITENTE, CONTRASENA)

        for i, alumno in enumerate(alumnos, start=1):
            nombre   = alumno.get("nombre", "").strip()
            email    = alumno.get("email", "").strip()
            texto    = alumno.get("texto", "").strip()
            adjunto  = alumno.get("fichero", "").strip()

            if not email:
                print(f"  [{i}/{total}] ⚠️  Sin email para {nombre}, omitido.")
                fallidos += 1
                continue

            try:
                msg = crear_correo(REMITENTE, email, ASUNTO, texto, adjunto or None)
                servidor.sendmail(REMITENTE, email, msg.as_string())
                print(f"  [{i}/{total}] ✅ Enviado a {nombre} <{email}>")
                enviados += 1
            except Exception as e:
                print(f"  [{i}/{total}] ❌ Error con {email}: {e}")
                errores.append((email, str(e)))
                fallidos += 1

    # Resumen final
    print(f"\n{'─'*45}")
    print(f"✅ Enviados:  {enviados}")
    print(f"❌ Fallidos:  {fallidos}")
    if errores:
        print("\nDetalle de errores:")
        for em, err in errores:
            print(f"  • {em}: {err}")


if __name__ == "__main__":
    enviar_correos(CSV_FICHERO)