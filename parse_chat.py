import re
import json
import os

chat_file = r"d:\mipanel\MaximusVpsMx\chatnuevo_export\Chat de WhatsApp con 🇦🇷Servidores solo para Argentina 🇦🇷💯 Gratis FreeLatamTeam 📲💪🇦🇷🇦🇷.txt"
output_file = r"c:\Users\JGJua\Nueva carpeta\MaximusWA\active_users.json"

active_numbers = set()

# Expresión regular para encontrar la estructura de la fecha/hora y atrapar el nombre del remitente
# Ejemplos:
# 15/04/24 10:20 - +52 1 861 199 5909: Hola
# 15/04/2024, 10:20 p. m. - Juan: Hola
pattern = re.compile(r"^\d{1,2}/\d{1,2}/\d{2,4}.*?(?:-|\])\s*(.*?):\s*(.*)", re.IGNORECASE)

with open(chat_file, "r", encoding="utf-8") as f:
    for line in f:
        match = pattern.search(line)
        if match:
            sender = match.group(1).strip()
            
            # Verificar si es un número de teléfono (contiene un '+')
            if sender.startswith("+"):
                # Limpiar el número para que quede solo dígitos (ej. 5491112345678)
                clean_number = re.sub(r"\D", "", sender)
                active_numbers.add(clean_number)

# Guardar la lista de números limpios en un JSON
with open(output_file, "w", encoding="utf-8") as f:
    json.dump(list(active_numbers), f, indent=2)

print(f"✅ Se encontraron {len(active_numbers)} números activos.")
print(f"✅ Archivo guardado en: {output_file}")
