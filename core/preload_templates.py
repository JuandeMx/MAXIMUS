#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Precargador de Plantillas .LT para MaximusVpsMx Master Panel
"""

import os
import sys
import json

# Importar parser
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from lt_parser import decrypt_profile

CONFIG_DIR = "/etc/MaximusVpsMx"
METHODS_DB = os.path.join(CONFIG_DIR, "connection_methods.db")

def import_all_plantillas():
    # Buscar la carpeta plantillas en /etc/MaximusVpsMx/plantillas o en la carpeta raíz del repo
    possible_dirs = [
        os.path.join(CONFIG_DIR, "plantillas"),
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "plantillas")
    ]

    PLANTILLAS_DIR = None
    for d in possible_dirs:
        if os.path.exists(d):
            PLANTILLAS_DIR = d
            break

    if not PLANTILLAS_DIR:
        print(f"[Preload] Directorio de plantillas no encontrado en ningún origen: {possible_dirs}")
        return

    files = [f for f in os.listdir(PLANTILLAS_DIR) if f.endswith(".LT") or f.endswith(".lt")]
    print(f"Encontrados {len(files)} archivos .LT en {PLANTILLAS_DIR}: {files}")

    lines = []
    if os.path.exists(METHODS_DB):
        with open(METHODS_DB, "r") as f:
            lines = f.readlines()

    imported_count = 0
    for filename in files:
        filepath = os.path.join(PLANTILLAS_DIR, filename)
        method_name = os.path.splitext(filename)[0] # Ej: "PERSONAL CF 1"

        try:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()

            data = decrypt_profile(content)
            if data:
                ssh_host = data.get("ssh_host", "")
                ssh_port = data.get("ssh_port", "22")
                protocol = data.get("protocol", "SSL + Payload (WebSocket)")
                sni = data.get("sni", "")
                payload = data.get("payload", "")

                # Formato en connection_methods.db:
                # name|ssh_host|ssh_port|ssh_user|ssh_pass|protocol|sni|payload
                lines = [l for l in lines if not l.startswith(f"{method_name}|")]
                lines.append(f"{method_name}|{ssh_host}|{ssh_port}|||{protocol}|{sni}|{payload}\n")
                imported_count += 1

                # Generar archivo físico .mx de descarga
                WEB_DIR = os.path.join(CONFIG_DIR, "web-panel")
                downloads_dir = os.path.join(WEB_DIR, "downloads")
                os.makedirs(downloads_dir, exist_ok=True)
                import re
                safe_name = re.sub(r'[^a-zA-Z0-9_\-]', '_', method_name)
                mx_filepath = os.path.join(downloads_dir, f"{safe_name}.mx")

                try:
                    from mx_generator import generate_mx_file
                    generate_mx_file(
                        name=method_name,
                        ssh_host=ssh_host,
                        ssh_port=int(ssh_port) if str(ssh_port).isdigit() else 22,
                        ssh_user="",
                        ssh_pass="",
                        sni=sni,
                        payload=payload,
                        out_path=mx_filepath
                    )
                except Exception as e_mx:
                    print(f"Error generando .mx para {method_name}: {e_mx}")

                print(f"✅ Método de Conexión '{method_name}' importado al panel.")
            else:
                print(f"❌ No se pudo descifrar: {filename}")
        except Exception as e:
            print(f"❌ Error procesando {filename}: {e}")

    with open(METHODS_DB, "w") as f:
        f.writelines(lines)

    print(f"🎉 Proceso finalizado: {imported_count} Métodos de Conexión precargados en {METHODS_DB}.")

if __name__ == "__main__":
    import_all_plantillas()
