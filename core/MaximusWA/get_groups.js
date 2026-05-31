if (typeof globalThis.crypto === 'undefined') {
    globalThis.crypto = require('crypto').webcrypto;
}
const { default: makeWASocket, useMultiFileAuthState, DisconnectReason, fetchLatestBaileysVersion } = require('@whiskeysockets/baileys');
const pino = require('pino');
const qrcode = require('qrcode-terminal');
const fs = require('fs');
const readline = require('readline');
const path = require('path');

const isWindows = process.platform === 'win32';
const AUTH_DIR = isWindows ? './wa_auth_info' : '/etc/MaximusVpsMx/wa_auth_info';
const GROUPS_FILE = isWindows ? './wa_groups.json' : '/etc/MaximusVpsMx/wa_groups.json';

// Ensure the directory exists
const targetDir = path.dirname(GROUPS_FILE);
if (!fs.existsSync(targetDir)) {
    fs.mkdirSync(targetDir, { recursive: true });
}

let connectionAttempts = 0;

async function start() {
    console.log('🤖 Iniciando conexión con WhatsApp... Por favor espera.');
    
    // Obtener la versión de WhatsApp Web más reciente
    let version = [2, 3000, 1017539726]; // Fallback estable
    try {
        const { version: latestVersion, isLatest } = await fetchLatestBaileysVersion();
        version = latestVersion;
        console.log(`[WA-BOT] Versión de WhatsApp Web detectada: ${version.join('.')}`);
    } catch (e) {
        console.log(`[WA-BOT] No se pudo obtener la versión actual de WA. Usando fallback: ${version.join('.')}`);
    }

    const { state, saveCreds } = await useMultiFileAuthState(AUTH_DIR);
    
    const sock = makeWASocket({
        version,
        auth: state,
        logger: pino({ level: 'silent' }),
        printQRInTerminal: true
    });

    sock.ev.on('creds.update', saveCreds);

    sock.ev.on('connection.update', async (update) => {
        const { connection, lastDisconnect } = update;
        
        if (connection === 'close') {
            const statusCode = lastDisconnect?.error?.output?.statusCode;
            const errorMsg = lastDisconnect?.error?.message || lastDisconnect?.error;
            console.log(`⚠️ Conexión cerrada. Código: ${statusCode}. Razón: ${errorMsg}`);
            
            // Si el estado es 401 (loggedOut), forzar cierre
            const isLoggedOut = statusCode === DisconnectReason.loggedOut;
            
            if (isLoggedOut) {
                console.log('❌ Sesión cerrada permanentemente o token inválido.');
                console.log('Limpiando credenciales antiguas para generar un código QR nuevo...');
                if (fs.existsSync(AUTH_DIR)) {
                    fs.rmSync(AUTH_DIR, { recursive: true, force: true });
                }
                setTimeout(() => start(), 2000);
                return;
            }

            connectionAttempts++;
            if (connectionAttempts > 5) {
                console.log('❌ Se detectaron múltiples fallos consecutivos al conectar.');
                console.log('Limpiando caché de credenciales temporales para solucionar el bucle...');
                if (fs.existsSync(AUTH_DIR)) {
                    // Borrar sólo los archivos de credenciales (dejar el store si es necesario) o borrar todo para QR nuevo
                    fs.rmSync(AUTH_DIR, { recursive: true, force: true });
                }
                connectionAttempts = 0;
                console.log('Reintentando conexión desde cero con QR nuevo...');
                setTimeout(() => start(), 3000);
                return;
            }

            console.log('🔄 Reintentando conectar en 5 segundos...');
            setTimeout(() => start(), 5000);
        } else if (connection === 'open') {
            connectionAttempts = 0;
            console.log('\n==================================================');
            console.log('   ✅ ¡CONECTADO CON ÉXITO A TU WHATSAPP!   ');
            console.log('==================================================\n');
            console.log('🔄 Sincronizando chats y obteniendo grupos... Espera 5 segundos.');
            
            try {
                // Wait for groups to sync fully
                await new Promise(resolve => setTimeout(resolve, 5000));
                
                console.log('🔍 Cargando lista de grupos...');
                const groups = await sock.groupFetchAllParticipating();
                const groupList = Object.values(groups);
                
                if (groupList.length === 0) {
                    console.log('⚠️ Alerta: Tu número de WhatsApp no participa en ningún grupo.');
                    console.log('Agrégate a un grupo e intenta de nuevo.');
                    process.exit(0);
                }

                console.log('\n📋 GRUPOS ENCONTRADOS:');
                console.log('==================================================');
                groupList.forEach((g, index) => {
                    console.log(` [${index + 1}] ➔ ${g.subject}`);
                });
                console.log('==================================================');
                
                const rl = readline.createInterface({
                    input: process.stdin,
                    output: process.stdout
                });

                const promptSelection = () => {
                    rl.question('\n👉 Selecciona los grupos que el bot va a administrar:\n' +
                                '   • Escribe el número del grupo (ej: 1)\n' +
                                '   • Múltiples números separados por comas (ej: 1,3,4)\n' +
                                '   • Escribe "all" o "todos" para administrar todos los grupos\n\n' +
                                'Opción seleccionada: ', (answer) => {
                        
                        const input = answer.trim().toLowerCase();
                        
                        if (input === 'all' || input === 'todos' || input === '') {
                            fs.writeFileSync(GROUPS_FILE, JSON.stringify(['all'], null, 2));
                            console.log('\n==================================================');
                            console.log('✅ CONFIGURADO: El bot administrará TODOS los grupos.');
                            console.log('==================================================\n');
                            rl.close();
                            process.exit(0);
                        }
                        
                        const indices = input.split(',')
                            .map(x => parseInt(x.trim()) - 1)
                            .filter(idx => !isNaN(idx));
                        
                        const selectedGroups = [];
                        let valid = true;
                        
                        indices.forEach(idx => {
                            if (idx >= 0 && idx < groupList.length) {
                                selectedGroups.push(groupList[idx].id);
                            } else {
                                valid = false;
                            }
                        });
                        
                        if (!valid || selectedGroups.length === 0) {
                            console.log('❌ Entrada no válida. Por favor, ingresa opciones del listado.');
                            promptSelection();
                            return;
                        }
                        
                        fs.writeFileSync(GROUPS_FILE, JSON.stringify(selectedGroups, null, 2));
                        console.log('\n==================================================');
                        console.log(`✅ CONFIGURADO: El bot administrará ${selectedGroups.length} grupo(s).`);
                        console.log('==================================================\n');
                        rl.close();
                        process.exit(0);
                    });
                };
                
                promptSelection();
                
            } catch (err) {
                console.error('❌ Error al obtener los grupos de WhatsApp:', err);
                process.exit(1);
            }
        }
    });
}

start().catch(err => {
    console.error('❌ Error al iniciar el gestor de grupos:', err);
    process.exit(1);
});
