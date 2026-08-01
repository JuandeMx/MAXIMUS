#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LT & MX File Parser / Converter for MaximusVpsMx Master Panel
Decrypts HTTP Custom / LTM / SocksHTTP encrypted profiles and converts them into Panel Method Templates.
"""

import sys
import os
import base64
import json
import xml.etree.ElementTree as ET
from Crypto.Cipher import AES
from Crypto.Protocol.KDF import PBKDF2
from Crypto.Hash import SHA1, SHA256

# Known encryption keys for .LT / .MX / SecurePreferences profiles
NATIVE_KEYS = [
    "909988c9f3714225aebace9546a08a6e7a83ceb66035498e95d23f784bbd8b99#$K@!",
    "SocksHttpSecretKeySecurePreferences2024",
    "fubgf777gf6",
    "freelatam123",
    "jgjua2026"
]

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
    "super", "ultra", "mega", "giga", "tera", "peta", "blaze", "storm"
]

def maze_deobfuscate(text):
    if not text or not isinstance(text, str) or not text.startswith(MAZE_PREFIX):
        return text
    body = text[len(MAZE_PREFIX):]
    try:
        raw = base64.b64decode(body)
        xor_decoded = bytearray()
        for i, b in enumerate(raw):
            xor_decoded.append(b ^ XOR_KEY[i % len(XOR_KEY)])
        
        words = xor_decoded.decode("utf-8", errors="ignore").split(" ")
        original_chars = []
        for word in words:
            if word in DICTIONARY:
                idx = DICTIONARY.index(word)
                original_chars.append(chr(idx))
            elif word.isdigit():
                original_chars.append(chr(int(word)))
        return "".join(original_chars)
    except Exception:
        return text

def decrypt_profile(raw_str):
    raw_str = raw_str.strip()
    if raw_str.startswith("\uFEFF"):
        raw_str = raw_str[1:]
    
    parts = raw_str.split(".")
    if len(parts) != 3:
        raise ValueError("Invalid format: expected 3 base64 dot-separated parts")

    salt = base64.b64decode(parts[0])
    iv = base64.b64decode(parts[1])
    cipher_text = base64.b64decode(parts[2])

    for key_str in NATIVE_KEYS:
        for hash_alg in [SHA256, SHA1]:
            for iterations in [1000]:
                for key_size in [16, 32]:
                    try:
                        key = PBKDF2(key_str, salt, dkLen=key_size, count=iterations, hmac_hash_module=hash_alg)
                        cipher = AES.new(key, AES.MODE_GCM, nonce=iv)
                        decrypted = cipher.decrypt(cipher_text)
                        xml_str = decrypted.decode("utf-8", errors="ignore")
                        if "<properties>" in xml_str or "<map>" in xml_str:
                            return parse_profile_xml(xml_str)
                    except Exception:
                        pass
    return None

def parse_profile_xml(xml_str):
    """Extrae las propiedades clave del XML descifrado"""
    result = {
        "ssh_host": "",
        "ssh_port": 22,
        "sni": "",
        "payload": "",
        "protocol": "SSH",
        "proxy_ip": "",
        "proxy_port": ""
    }
    
    try:
        root = ET.fromstring(xml_str)
        # Soporta formatos <map> y <properties>
        props = {}
        for child in root:
            name = child.attrib.get("name") or child.attrib.get("key")
            val = child.text or ""
            if name:
                props[name] = maze_deobfuscate(val)
        
        result["ssh_host"] = props.get("sshServer", props.get("serverHost", props.get("ssh_host", props.get("server", ""))))
        result["ssh_port"] = props.get("sshPort", props.get("serverPort", props.get("ssh_port", "22")))
        result["sni"] = props.get("customSNI", props.get("customSni", props.get("sni", props.get("sslHost", ""))))
        result["payload"] = props.get("proxyPayload", props.get("customPayload", props.get("payload", props.get("httpPayload", ""))))
        result["proxy_ip"] = props.get("proxyRemoto", props.get("proxyHost", props.get("proxy_ip", "")))
        result["proxy_port"] = props.get("proxyRemotoPorta", props.get("proxyPort", props.get("proxy_port", "")))
        
        # Determinar protocolo
        use_ssl = props.get("use_ssl", "0") == "1"
        use_payload = props.get("use_payload", "0") == "1"
        use_v2ray = props.get("use_v2ray", "0") == "1"
        if use_v2ray:
            result["protocol"] = "V2RAY"
        elif use_ssl and use_payload:
            result["protocol"] = "SSL + Payload (WebSocket)"
        elif use_ssl:
            result["protocol"] = "SSL / TLS"
        else:
            result["protocol"] = "HTTP DIRECT / PAYLOAD"
            
    except Exception as e:
        print(f"Error parsing XML: {e}")
        
    return result

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python lt_parser.py <file.lt>")
        sys.exit(1)
        
    file_path = sys.argv[1]
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()
        
    res = decrypt_profile(content)
    if res:
        print(json.dumps(res, indent=2, ensure_ascii=False))
    else:
        print("Failed to decrypt profile.")
