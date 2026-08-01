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
TEMPLATES_DB = os.path.join(CONFIG_DIR, "method_templates.db")
PLANTILLAS_DIR = os.path.join(CONFIG_DIR, "plantillas")

def import_all_plantillas():
    if not os.path.exists(PLANTILLAS_DIR):
        print(f"Directorio de plantillas no encontrado: {PLANTILLAS_DIR}")
        return

    files = [f for f in os.listdir(PLANTILLAS_DIR) if f.endswith(".LT") or f.endswith(".lt")]
    print(f"Encontrados {len(files)} archivos .LT en {PLANTILLAS_DIR}: {files}")

    lines = []
    if os.path.exists(TEMPLATES_DB):
        with open(TEMPLATES_DB, "r") as f:
            lines = f.readlines()

    imported_count = 0
    for filename in files:
        filepath = os.path.join(PLANTILLAS_DIR, filename)
        template_name = os.path.splitext(filename)[0] # Ej: "PERSONAL CF 1"

        try:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()

            data = decrypt_profile(content)
            if data:
                protocol = data.get("protocol", "SSL + Payload (WebSocket)")
                sni = data.get("sni", "")
                payload = data.get("payload", "")

                # Evitar duplicados
                lines = [l for l in lines if not l.startswith(f"{template_name}|")]
                lines.append(f"{template_name}|{protocol}|{sni}|{payload}\n")
                imported_count += 1
                print(f"✅ Plantilla '{template_name}' descifrada e importada.")
            else:
                print(f"❌ No se pudo descifrar: {filename}")
        except Exception as e:
            print(f"❌ Error procesando {filename}: {e}")

    with open(TEMPLATES_DB, "w") as f:
        f.writelines(lines)

    print(f"🎉 Proceso finalizado: {imported_count} plantillas precargadas en {TEMPLATES_DB}.")

if __name__ == "__main__":
    import_all_plantillas()
