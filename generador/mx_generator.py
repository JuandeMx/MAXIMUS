#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
========================================================================
GENERADOR OFICIAL DE ARCHIVOS .MX - PANEL MAESTRO MAXIMUS
========================================================================
Este script genera archivos de configuración encriptados (.mx) compatibles
al 100% con la aplicación Android MAXIMUS Net / SocksHTTP.

Uso por Línea de Comandos:
  python mx_generator.py --name "TELCEL SSL ILIMITADO" --host "187.209.14.58" --port 22 --sni "m.facebook.com" --payload "GET / HTTP/1.1[crlf]Host: m.facebook.com[crlf][crlf]" --out "telcel.mx"

Uso como Módulo en Python (Para tu servidor web Backend Maestro):
  from mx_generator import generate_mx_file
  mx_bytes = generate_mx_file(name="BITEL", ssh_host="187.209.14.58", ssh_port=22, sni="m.facebook.com")
"""

import sys
import os
import argparse
import base64
import hashlib
import json
import xml.etree.ElementTree as ET
from xml.dom import minidom
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
from Crypto.Protocol.KDF import PBKDF2
from Crypto.Hash import SHA1, SHA256

# CLAVE SECRETA DE ENCRIPTACIÓN DE LA APP
NATIVE_SECURE_KEY = "SocksHttpSecretKeySecurePreferences2024"
MAZE_PREFIX = "sec_maze:"

XOR_KEY = [0x5A, 0xA5, 0xF0, 0x0F, 0xC3, 0x3C, 0xAA, 0x55]

DICTIONARY = [
    "alpha", "bravo", "charlie", "delta", "echo", "foxtrot", "golf", "hotel",
    "india", "juliet", "kilo", "lima", "mike", "november", "oscar", "papa",
    "quebec", "romeo", "sierra", "tango", "uniform", "victor", "whiskey", "xray",
    "yankee", "zulu", "zero", "one", "two", "three", "four", "five", "six",
    "seven", "eight", "nine", "star", "orbit", "galaxy", "pulse", "cyber",
    "matrix", "quantum", "vector", "nexus", "vertex", "prism", "shadow", "ghost",
    "viper", "falcon", "raven", "phoenix", "titan", "atlas", "hyper", "turbo",
    "super", "ultra", "mega", "giga", "tera", "peta", "blaze", "storm",
    "thunder", "frost", "inferno", "apex", "zenith", "nadir", "vortex", "cosmo",
    "astro", "lunar", "solar", "stellar", "nebula", "comet", "meteor", "pulsar",
    "quasar", "aurora", "corona", "eclipse", "horizon", "equinox", "solstice", "beacon",
    "signal", "beacon", "radar", "sonar", "laser", "photon", "proton", "electron",
    "neutron", "quark", "lepton", "boson", "hadron", "muon", "tau", "gluon",
    "graviton", "tachy", "plasma", "magma", "lava", "crystal", "gem", "diamond",
    "ruby", "sapphire", "emerald", "topaz", "opal", "amber", "pearl", "jade",
    "onyx", "quartz", "flint", "slate", "granite", "marble", "basalt", "pumice",
    "obsidian", "silver", "gold", "copper", "iron", "steel", "bronze", "brass",
    "cobalt", "nickel", "chrome", "titanium", "platinum", "zinc", "tin", "lead",
    "bismuth", "carbon", "silicon", "sulfur", "sodium", "argon", "krypton", "xenon",
    "neon", "helium", "lithium", "boron", "radon", "ferrum", "aurum", "argentum",
    "plumbum", "cuprum", "stannum", "hydra", "draco", "orion", "cygnus", "lyra",
    "pegasus", "taurus", "aries", "gemini", "cancer", "leo", "virgo", "libra",
    "scorpio", "sagittar", "capricorn", "aquarius", "pisces", "phoenix", "centaur", "pegasus",
    "griffin", "chimera", "sphinx", "kraken", "golem", "titan", "giant", "cyclops", "gorgon",
    "siren", "harpy", "minotaur", "valkyrie", "banshee", "specter", "wraith", "phantom",
    "shadow", "shade", "spirit", "demon", "angel", "seraph", "cherub", "deity"
]

def maze_xor(data_bytes):
    out = bytearray()
    for i, b in enumerate(data_bytes):
        out.append(b ^ XOR_KEY[i % len(XOR_KEY)])
    return bytes(out)

def maze_encrypt(text):
    if not text:
        return ""
    data = text.encode("utf-8")
    obf = maze_xor(data)
    words = []
    for b in obf:
        words.append(DICTIONARY[b % len(DICTIONARY)])
    return MAZE_PREFIX + " ".join(words)

def cryptor_encrypt_to_base64(data_bytes, password_str=NATIVE_SECURE_KEY):
    salt = get_random_bytes(16)
    iv = get_random_bytes(16)

    derived_key = PBKDF2(password_str.encode("utf-8"), salt, dkLen=32, count=1000, hmac_hash_module=SHA256)
    cipher = AES.new(derived_key, AES.MODE_CBC, iv)

    pad_len = 16 - (len(data_bytes) % 16)
    padded_data = data_bytes + bytes([pad_len] * pad_len)

    cipher_text = cipher.encrypt(padded_data)

    salt_b64 = base64.b64encode(salt).decode("utf-8")
    iv_b64 = base64.b64encode(iv).decode("utf-8")
    cipher_b64 = base64.b64encode(cipher_text).decode("utf-8")

    return f"{salt_b64}.{iv_b64}.{cipher_b64}"

def build_properties_xml(name, ssh_host, ssh_port=22, ssh_user="", ssh_pass="", sni="", payload="", is_ssl=False, is_payload=False):
    root = ET.Element("properties")

    entries = {
        "file.appVersionCode": "24",
        "file.proteger": "1",
        "file.msg": f"Perfil MAXIMUS: {name}",
        "file.hideServerMessage": "0",
        "file.pedirLogin": "0" if (ssh_user and ssh_pass) else "1",
        "bloquearRoot": "0",
        "ssh_hwid": "0",
        "file.validade": "0",
        "sshServer": maze_encrypt(ssh_host),
        "sshPort": maze_encrypt(str(ssh_port)),
        "sshUser": maze_encrypt(ssh_user),
        "sshPass": maze_encrypt(ssh_pass),
        "sshPortaLocal": "1080",
        "tunnelType": "3" if is_ssl else ("2" if is_payload else "1"),
        "dnsForward": "1",
        "dnsResolver": "8.8.8.8",
        "udpForward": "0",
        "udpResolver": "8.8.8.8",
        "proxyRemoto": maze_encrypt(""),
        "proxyRemotoPorta": maze_encrypt(""),
        "usarDefaultPayload": "0" if payload else "1",
        "proxyPayload": maze_encrypt(payload.replace("[crlf]", "\r\n").replace("[CRLF]", "\r\n")),
        "customSNI": maze_encrypt(sni),
        "unified_input": maze_encrypt(f"{ssh_host}:{ssh_port}@{ssh_user}:{ssh_pass}"),
        "use_ssl": "1" if is_ssl else "0",
        "use_payload": "1" if is_payload else "0",
        "use_enhanced": "0",
        "use_slowdns": "0",
        "use_psiphon": "0",
        "use_v2ray": "0",
        "v2ray_config": maze_encrypt("")
    }

    for k, v in entries.items():
        entry = ET.SubElement(root, "entry", key=k)
        entry.text = v

    rough_bytes = ET.tostring(root, encoding="utf-8")
    reparsed = minidom.parseString(rough_bytes)
    return reparsed.toprettyxml(indent="  ", encoding="utf-8")

def generate_mx_file(name, ssh_host, ssh_port=22, ssh_user="", ssh_pass="", sni="", payload="", out_path=None):
    proto_upper = (sni + payload).upper()
    is_ssl = bool(sni)
    is_payload = bool(payload)

    xml_bytes = build_properties_xml(name, ssh_host, ssh_port, ssh_user, ssh_pass, sni, payload, is_ssl, is_payload)
    mx_encrypted_str = cryptor_encrypt_to_base64(xml_bytes)

    if out_path:
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(mx_encrypted_str)

    return mx_encrypted_str

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generador de archivos .MX para MAXIMUS Net / SocksHTTP")
    parser.add_argument("--name", required=True, help="Nombre del perfil (ej. TELCEL SSL)")
    parser.add_argument("--host", required=True, help="IP o Dominio SSH (ej. 187.209.14.58)")
    parser.add_argument("--port", type=int, default=22, help="Puerto SSH (ej. 22)")
    parser.add_argument("--user", default="", help="Usuario SSH (opcional)")
    parser.add_argument("--pass", dest="ssh_pass", default="", help="Contraseña SSH (opcional)")
    parser.add_argument("--sni", default="", help="SNI (ej. m.facebook.com)")
    parser.add_argument("--payload", default="", help="Payload (ej. GET / HTTP/1.1[crlf]Host: m.facebook.com[crlf][crlf])")
    parser.add_argument("--out", help="Ruta del archivo de salida .mx (ej. perfil.mx)")

    args = parser.parse_args()

    res = generate_mx_file(
        name=args.name,
        ssh_host=args.host,
        ssh_port=args.port,
        ssh_user=args.user,
        ssh_pass=args.ssh_pass,
        sni=args.sni,
        payload=args.payload,
        out_path=args.out
    )

    if args.out:
        print(f"[+] Archivo .mx generado exitosamente en: {args.out}")
    else:
        print("[+] Contenido encriptado .MX:")
        print(res)
