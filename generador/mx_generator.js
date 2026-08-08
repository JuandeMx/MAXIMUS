/**
 * ========================================================================
 * GENERADOR NATIVO NODE.JS DE ARCHIVOS .MX - PANEL MAESTRO MAXIMUS
 * ========================================================================
 * Este script genera archivos .MX cifrados utilizando la librería 'crypto'
 * integrada de Node.js (Sin dependencias externas).
 * 
 * Uso en Consola:
 *   node mx_generator.js --name "TELCEL SSL ILIMITADO" --host "187.209.14.58" --port 22 --sni "m.facebook.com" --out "telcel.mx"
 * 
 * Uso en tu servidor Express / Node.js Backend Maestro:
 *   const { generateMxContent } = require('./mx_generator');
 *   const mxContent = generateMxContent({ name: "BITEL", host: "187.209.14.58", port: 22, sni: "m.facebook.com" });
 */

const crypto = require('crypto');
const fs = require('fs');

const NATIVE_SECURE_KEY = "SocksHttpSecretKeySecurePreferences2024";
const MAZE_PREFIX = "sec_maze:";
const XOR_KEY = Buffer.from([0x5A, 0xA5, 0xF0, 0x0F, 0xC3, 0x3C, 0xAA, 0x55]);

const DICTIONARY = [
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
];

function mazeEncrypt(text) {
    if (!text || text === "") return "";
    const buf = Buffer.from(text, 'utf8');
    const words = [];
    for (let i = 0; i < buf.length; i++) {
        const xorByte = buf[i] ^ XOR_KEY[i % XOR_KEY.length];
        words.push(DICTIONARY[xorByte % DICTIONARY.length]);
    }
    return MAZE_PREFIX + words.join(" ");
}

function encryptCryptorBase64(dataBuffer, secretKey = NATIVE_SECURE_KEY) {
    const salt = crypto.randomBytes(16);
    const iv = crypto.randomBytes(16);

    const derivedKey = crypto.pbkdf2Sync(secretKey, salt, 1000, 32, 'sha256');

    const cipher = crypto.createCipheriv('aes-256-cbc', derivedKey, iv);
    let encrypted = cipher.update(dataBuffer);
    encrypted = Buffer.concat([encrypted, cipher.final()]);

    const saltB64 = salt.toString('base64');
    const ivB64 = iv.toString('base64');
    const cipherB64 = encrypted.toString('base64');

    return `${saltB64}.${ivB64}.${cipherB64}`;
}

function generatePropertiesXml({ name, host, port = 22, user = "", pass = "", sni = "", payload = "" }) {
    const isSsl = Boolean(sni);
    const isPayload = Boolean(payload);

    const cleanPayload = payload ? payload.replace(/\[crlf\]/gi, "\r\n") : "";

    const entries = {
        "file.appVersionCode": "24",
        "file.proteger": "1",
        "file.msg": `Perfil MAXIMUS: ${name}`,
        "file.hideServerMessage": "0",
        "file.pedirLogin": (user && pass) ? "0" : "1",
        "bloquearRoot": "0",
        "ssh_hwid": "0",
        "file.validade": "0",
        "sshServer": mazeEncrypt(host),
        "sshPort": mazeEncrypt(String(port)),
        "sshUser": mazeEncrypt(user),
        "sshPass": mazeEncrypt(pass),
        "sshPortaLocal": "1080",
        "tunnelType": isSsl ? "3" : (isPayload ? "2" : "1"),
        "dnsForward": "1",
        "dnsResolver": "8.8.8.8",
        "udpForward": "0",
        "udpResolver": "8.8.8.8",
        "proxyRemoto": mazeEncrypt(""),
        "proxyRemotoPorta": mazeEncrypt(""),
        "usarDefaultPayload": payload ? "0" : "1",
        "proxyPayload": mazeEncrypt(cleanPayload),
        "customSNI": mazeEncrypt(sni),
        "unified_input": mazeEncrypt(`${host}:${port}@${user}:${pass}`),
        "use_ssl": isSsl ? "1" : "0",
        "use_payload": isPayload ? "1" : "0",
        "use_enhanced": "0",
        "use_slowdns": "0",
        "use_psiphon": "0",
        "use_v2ray": "0",
        "v2ray_config": mazeEncrypt("")
    };

    let xml = `<?xml version="1.0" encoding="UTF-8"?>\n`;
    xml += `<!DOCTYPE properties SYSTEM "http://java.sun.com/dtd/properties.dtd">\n`;
    xml += `<properties>\n`;
    for (const [k, v] of Object.entries(entries)) {
        xml += `  <entry key="${k}">${v}</entry>\n`;
    }
    xml += `</properties>`;

    return Buffer.from(xml, 'utf8');
}

function generateMxContent(options) {
    const xmlBuffer = generatePropertiesXml(options);
    return encryptCryptorBase64(xmlBuffer);
}

if (require.main === module) {
    const args = process.argv.slice(2);
    const params = {};
    for (let i = 0; i < args.length; i += 2) {
        const key = args[i].replace(/^--/, '');
        const val = args[i + 1] || '';
        params[key] = val;
    }

    if (!params.name || !params.host) {
        console.log("==========================================================");
        console.log("   GENERADOR DE ARCHIVOS .MX - PANEL MAESTRO MAXIMUS");
        console.log("==========================================================");
        console.log("Uso:");
        console.log("  node mx_generator.js --name \"TELCEL SSL\" --host \"187.209.14.58\" --port 22 --sni \"m.facebook.com\" --out \"telcel.mx\"");
        console.log("==========================================================");
        process.exit(0);
    }

    const mxEncrypted = generateMxContent(params);

    if (params.out) {
        fs.writeFileSync(params.out, mxEncrypted, 'utf8');
        console.log(`[+] Archivo .MX generado exitosamente en: ${params.out}`);
    } else {
        console.log("[+] Contenido .MX encriptado:");
        console.log(mxEncrypted);
    }
}

module.exports = {
    generateMxContent
};
