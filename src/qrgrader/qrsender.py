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
import argparse
import smtplib
import csv
import os
import sys
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

import pandas
import yaml

from qrgrader.code import Code
from qrgrader.code_set import CodeSet
from qrgrader.common import StudentsData, Nia, get_workspace_paths, get_date

# ──────────────────────────────────────────────
# CONFIGURACIÓN — edita estos valores
# ──────────────────────────────────────────────
SMTP_SERVER   = "smtp.gmail.com"        # Gmail. Outlook: smtp.office365.com
SMTP_PORT     = 587

# ──────────────────────────────────────────────


def crear_correo(remitente, destinatario, asunto, cuerpo, ruta_adjuntos=None):
    """Construye el mensaje MIME con texto y adjunto opcional."""
    msg = MIMEMultipart()
    msg["From"]    = remitente
    msg["To"]      = destinatario
    msg["Subject"] = asunto

    msg.attach(MIMEText(cuerpo, "plain", "utf-8"))
    ruta_adjuntos = ruta_adjuntos or []
    for ruta_adjunto in ruta_adjuntos:
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

        email    = alumno.get("email", "").strip()
        texto    = alumno.get("texto", "").strip()
        adjuntos  = alumno.get("ficheros", [])
        asunto   = alumno.get("asunto", "").strip()

        try:
            msg = crear_correo(REMITENTE, email, asunto, texto, adjuntos or None)
            servidor.sendmail(REMITENTE, email, msg.as_string())
            return True, None
        except Exception as e:
            return False, str(e)


def main():
    parser = argparse.ArgumentParser(description='Patching and detection')

    parser.add_argument('-f', '--file', help='YAML file', default=None)
    parser.add_argument('-l', '--list', help='List of students', action="store_true")
    parser.add_argument('-b', '--begin', help='First exam to be sent', type=int, default=0)

    args = parser.parse_args()

    dir_workspace, dir_data, dir_scanned, dir_generated, dir_xls, dir_publish, dir_source = get_workspace_paths(os.getcwd())
    nias = Nia()
    prefix = get_date() + "_"
    nias.from_codes_file(dir_data + prefix + "detected.csv")
    students = StudentsData(dir_xls + prefix + "data.csv")
    if not students.load():
        print("Students data file not found")

    if args.list:
        for i, nia in enumerate(nias.get_all_nias()):
            nia = int(nia)
            exam_id = nias.get_exam(nia)  # Load exam IDs for all NIAs
            name = students.get_name(nia)  # Load names for all NIAs
            email = students.get_email(nia).strip()
            print(f"{i:3d}  {exam_id}  {email}  {name}")
        return

    if args.file:
        if not os.path.isfile(args.file):
            print(f"YAML file not found: {args.file}")
            return
    else:
        print("YAML file is required. Use -f <file> to specify the file.")
        return

    with open(args.file, newline='', encoding='utf-8') as csvfile:
        master = yaml.safe_load(csvfile)

    for i, nia in enumerate(nias.get_all_nias()):
        if i >= args.begin:
            nia = int(nia)
            exam_id = nias.get_exam(nia)  # Load exam IDs for all NIAs
            name = students.get_name(nia)  # Load names for all NIAs
            email = students.get_email(nia).strip()
            alumno = master.copy()
            alumno["email"] =  f"{email}"
            alumno["email"] = "dantard@unizar.es"
            alumno["ficheros"] = [f"{dir_publish}{exam_id}.pdf"]
            alumno["texto"] = alumno["texto"].replace("{name}", name)
            alumno["asunto"] = alumno["asunto"].replace("{name}", name)
            ok, msg = enviar_correos(alumno)
            if ok:
                print(f"Sent exam {i:3d} -> {exam_id} to {email}")
            else:
                print(f"Error sending exam {i} -> {exam_id} to {email}: {msg}")

            time.sleep(1)

if __name__ == "__main__":
    main()
