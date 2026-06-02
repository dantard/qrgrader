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
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

import pandas

from qrgrader.code import Code
from qrgrader.code_set import CodeSet
from qrgrader.common import StudentsData, Nia, get_workspace_paths, get_date

# ──────────────────────────────────────────────
# CONFIGURACIÓN — edita estos valores
# ──────────────────────────────────────────────
SMTP_SERVER   = "smtp.gmail.com"        # Gmail. Outlook: smtp.office365.com
SMTP_PORT     = 587
REMITENTE     = "xxxxxxxx"
CONTRASENA    = "ibxadwygsoxirmfvyngs"  # Ver nota al final
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


def enviar_correos(alumno):
    enviados  = 0
    fallidos  = 0
    errores   = []

    # Conectar al servidor SMTP una sola vez (más eficiente)
    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as servidor:
        servidor.ehlo()
        servidor.starttls()
        servidor.login(REMITENTE, CONTRASENA)

        nombre   = alumno.get("nombre", "").strip()
        email    = alumno.get("email", "").strip()
        texto    = alumno.get("texto", "").strip()
        adjunto  = alumno.get("fichero", "").strip()

        try:
            msg = crear_correo(REMITENTE, email, ASUNTO, texto, adjunto or None)
            servidor.sendmail(REMITENTE, email, msg.as_string())
            return True, None
        except Exception as e:
            return False, str(e)


def main():
    dir_workspace, dir_data, dir_scanned, dir_generated, dir_xls, dir_publish, dir_source = get_workspace_paths(os.getcwd())
    prefix = get_date() + "_"
    df = pandas.read_csv(dir_xls + prefix + "raw.csv", sep='\t', header=0)
    print(df.head())



    '''
    alumno = {"nombre": "Danilo", "email": "daniletto@gmail.com",
              "texto": "Hola Danilo, tu nota es un 10..."}
              #"fichero": "/home/danilo/T08B_informe_valoracion_tesis_doctoral.pdf"}
    for i in range(300):
        ok, msg = enviar_correos(alumno)
        print(i, ok, msg)
        time.sleep(1)
    '''

if __name__ == "__main__":
    main()