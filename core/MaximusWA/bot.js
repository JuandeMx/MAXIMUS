if (typeof globalThis.crypto === 'undefined') {
    globalThis.crypto = require('crypto').webcrypto;
}
const { default: makeWASocket, useMultiFileAuthState, DisconnectReason, fetchLatestBaileysVersion } = require('@whiskeysockets/baileys');
const pino = require('pino');
const fs = require('fs');
const path = require('path');

const isWindows = process.platform === 'win32';
const AUTH_DIR = isWindows ? './wa_auth_info' : '/etc/MaximusVpsMx/wa_auth_info';
const GROUPS_FILE = isWindows ? './wa_groups.json' : '/etc/MaximusVpsMx/wa_groups.json';
const SETTINGS_FILE = isWindows ? './wa_mod_settings.json' : '/etc/MaximusVpsMx/wa_mod_settings.json';

// Ensure config dir exists
const targetDir = path.dirname(SETTINGS_FILE);
if (!fs.existsSync(targetDir)) {
    fs.mkdirSync(targetDir, { recursive: true });
}

// Persistency database
let settings = { groups: {}, moderators: [] };

function loadSettings() {
    try {
        if (fs.existsSync(SETTINGS_FILE)) {
            settings = JSON.parse(fs.readFileSync(SETTINGS_FILE, 'utf8'));
        }
        if (!settings.moderators) {
            settings.moderators = [];
        }
    } catch (e) {
        console.error('[WA-BOT] Error al cargar wa_mod_settings.json:', e);
    }
}

function saveSettings() {
    try {
        fs.writeFileSync(SETTINGS_FILE, JSON.stringify(settings, null, 2));
    } catch (e) {
        console.error('[WA-BOT] Error al guardar wa_mod_settings.json:', e);
    }
}

// Setup defaults for a group JID
function getGroupSettings(chatJid) {
    if (!settings.groups[chatJid]) {
        settings.groups[chatJid] = {
            antilink: true, // Por defecto activado
            badwords_active: false,
            badwords: [],
            welcome_active: true,
            welcome_message: '👋 Bienvenidos al grupo:\n{users}\n\nPRIMER Y ÚLTIMO AVISO: Todo usuario nuevo tiene 60 MINUTOS exactos para identificarse. Quien no lo haga, será purgado del Grupo sin previo aviso.\n\n FORMATO OBLIGATORIO:\n Nombre | País | Compañía\n\n CÓDIGO DE CONDUCTA (TOLERANCIA CERO):\n\nREPORTES: El uso del servicio sin captura de pantalla se considera actividad sospechosa. Reporta o vete.\nCERO COMERCIO: El intento de venta o spam resultará en un BAN PERMANENTE e IRREVOCABLE.\nLIMPIEZA DE INACTIVOS: No mantenemos "fantasmas". Si no aportas, dejas el espacio para alguien que sí sea útil.\n\n REGLAS DEL GRUPO \n \n 1. RESPETO OBLIGATORIO\nQueda totalmente prohibido faltar al respeto, insultar o burlarse de cualquier miembro. Respetamos a todos por igual, sin importar quién sea.\n \n 2. PROHIBIDO COMPARTIR ENLACES\nNo se permite enviar ningún tipo de link, invitación a otros grupos o páginas externas.\n \n 3. PROHIBIDO STICKERS "SARPADOS"\nNo mandar stickers ofensivos, con contenido sexual, violento o que incomoden a los demás. Mantengamos el grupo limpio.\n \n 4. NO MOLESTAR AL PRIVADO\nNo escriban al privado a los usuarios para pedir cosas o vender. Cualquier duda o consulta, háganla aquí en el grupo o pregunten directamente a los ADMINISTRADORES.\n \n 5. PROHIBIDO LUCRAR\nEstá terminantemente prohibido vender, cobrar o hacer negocios con lo que se comparte aquí. El grupo es de ayuda y GRATIS.\n \n 6. COMPRAS DE MATERIAL EXPLOSIVO\nSi desean comprar algo explosivo o material relacionado, HABLAR ÚNICAMENTE Y EXCLUSIVAMENTE CON LOS ADMINISTRADORES. No pregunten ni oferten en el chat general.\n\n EL QUE NO CUMPLA SERÁ ELIMINADO AUTOMÁTICAMENTE SIN AVISO',
            pendingWelcomes: [],
            pendingPresentations: {}
        };
        saveSettings();
    }
    const g = settings.groups[chatJid];
    if (!g.pendingWelcomes) g.pendingWelcomes = [];
    if (!g.pendingPresentations) g.pendingPresentations = {};
    return g;
}

// Helper to extract text
function getMessageText(message) {
    try {
        if (!message) return '';
        return message.conversation || 
               (message.extendedTextMessage && message.extendedTextMessage.text) || 
               (message.imageMessage && message.imageMessage.caption) || 
               '';
    } catch (e) {
        return '';
    }
}

// Check presentation format (Nombre, País, Compañía)
function isValidPresentation(text) {
    try {
        if (!text) return false;
        // Normalizar texto quitando acentos y mayúsculas
        const clean = text.toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "");
        
        // Buscar indicios de Nombre
        const hasName = clean.includes('nombre') || clean.includes('llamo') || clean.includes('name');
        
        // Buscar indicios de País
        const hasCountry = clean.includes('pais') || clean.includes('de:') || clean.includes('soy de') || clean.includes('country') || clean.includes('ubicacion');
        
        // Buscar indicios de Compañía
        const hasCompany = clean.includes('compania') || clean.includes('empresa') || clean.includes('trabajo') || clean.includes('firma') || clean.includes('compañia');
        
        return hasName && hasCountry && hasCompany;
    } catch (e) {
        return false;
    }
}

// Metadata cache
const metadataCache = new Map();

async function getGroupMetadata(chatJid, sock, force = false) {
    if (!force && metadataCache.has(chatJid)) {
        return metadataCache.get(chatJid);
    }
    try {
        const metadata = await sock.groupMetadata(chatJid);
        metadataCache.set(chatJid, metadata);
        // Expire cache after 5 minutes
        setTimeout(() => metadataCache.delete(chatJid), 5 * 60 * 1000);
        return metadata;
    } catch (e) {
        console.error(`[WA-BOT] Error al obtener metadatos de ${chatJid}:`, e);
        return null;
    }
}

// Admin privileges check
async function checkAdmins(chatJid, senderJid, sock) {
    try {
        // 1. Verificar si el remitente está en la lista de moderadores globales del bot
        const globalMods = settings.moderators || [];
        if (globalMods.includes(senderJid)) {
            return { isSenderAdmin: true, isBotAdmin: true };
        }

        const metadata = await getGroupMetadata(chatJid, sock);
        if (!metadata) return { isSenderAdmin: false, isBotAdmin: false };
        
        if (!sock || !sock.user || !sock.user.id) {
            return { isSenderAdmin: false, isBotAdmin: false };
        }
        const botJid = sock.user.id.split(':')[0] + '@s.whatsapp.net';
        const participants = metadata.participants || [];
        
        const sender = participants.find(p => p.id === senderJid);
        const bot = participants.find(p => p.id === botJid);
        
        const isSenderAdmin = sender && (sender.admin === 'admin' || sender.admin === 'superadmin' || sender.id === botJid);
        const isBotAdmin = bot && (bot.admin === 'admin' || bot.admin === 'superadmin');
        
        return { isSenderAdmin: !!isSenderAdmin, isBotAdmin: !!isBotAdmin };
    } catch (e) {
        console.error('[WA-BOT] Error en checkAdmins:', e);
        return { isSenderAdmin: false, isBotAdmin: false };
    }
}

// Extract target user for moderation commands (.kick, .warn, .approve)
function getTargetJid(msg, parts) {
    const repliedJid = msg.message?.extendedTextMessage?.contextInfo?.participant;
    if (repliedJid) return repliedJid;

    const mentions = msg.message?.extendedTextMessage?.contextInfo?.mentionedJid || [];
    if (mentions.length > 0) return mentions[0];

    if (parts[1]) {
        let clean = parts[1].replace(/[^0-9]/g, '');
        if (clean.length >= 10) {
            return `${clean}@s.whatsapp.net`;
        }
    }
    return null;
}

// Send batch welcome message
async function sendBatchWelcome(chatJid, sock) {
    try {
        const groupSet = getGroupSettings(chatJid);
        if (groupSet.pendingWelcomes.length === 0) return;

        const metadata = await getGroupMetadata(chatJid, sock);
        const groupName = metadata ? metadata.subject : 'el grupo';
        
        // Obtener los primeros 5 o todos si se fuerza
        const toWelcome = groupSet.pendingWelcomes.slice(0, 5);
        groupSet.pendingWelcomes = groupSet.pendingWelcomes.slice(5);
        saveSettings();

        // Crear lista de tags
        const tagsStr = toWelcome.map(jid => `@${jid.split('@')[0]}`).join(', ');
        
        let welcomeTxt = groupSet.welcome_message;
        welcomeTxt = welcomeTxt.replace(/{users}/g, tagsStr);
        welcomeTxt = welcomeTxt.replace(/{group}/g, groupName);

        await sock.sendMessage(chatJid, {
            text: welcomeTxt,
            mentions: toWelcome
        });
    } catch (e) {
        console.error('[WA-BOT] Error al enviar bienvenida colectiva:', e);
    }
}

// Periodic task checking for expired presentations (checks every 30 seconds)
function startAutoKickTimer(sock) {
    console.log('🕒 Temporizador de Auto-Expulsión iniciado (Revisión cada 30 seg)...');
    setInterval(async () => {
        try {
            loadSettings();
            const now = Date.now();
            const oneHour = 3600000; // 1 hora en milisegundos

            for (const chatJid of Object.keys(settings.groups)) {
                const groupSet = settings.groups[chatJid];
                if (!groupSet.pendingPresentations) continue;

                const pendingJids = Object.keys(groupSet.pendingPresentations);
                if (pendingJids.length === 0) continue;

                let changed = false;

                for (const userJid of pendingJids) {
                    const joinTime = groupSet.pendingPresentations[userJid];
                    if (now - joinTime > oneHour) {
                        console.log(`[WA-BOT] Plazo expirado de presentación para @${userJid.split('@')[0]} en ${chatJid}`);
                        
                        const { isBotAdmin } = await checkAdmins(chatJid, userJid, sock);
                        
                        if (isBotAdmin) {
                            try {
                                // Expulsar al usuario
                                await sock.groupParticipantsUpdate(chatJid, [userJid], 'remove');
                                
                                // Enviar notificación al grupo
                                await sock.sendMessage(chatJid, {
                                    text: `⏰ @${userJid.split('@')[0]} ha sido expulsado automáticamente por no presentarse (Nombre, País, Compañía) dentro del plazo de 1 hora.`,
                                    mentions: [userJid]
                                });
                            } catch (e) {
                                console.error(`[WA-BOT] Error al expulsar a ${userJid}:`, e);
                            }
                        } else {
                            console.log(`[WA-BOT] No se pudo expulsar a ${userJid} porque el bot no es administrador.`);
                        }

                        // Eliminar de pendientes para no volver a evaluar
                        delete groupSet.pendingPresentations[userJid];
                        changed = true;
                    }
                }

                if (changed) {
                    saveSettings();
                }
            }
        } catch (err) {
            console.error('[WA-BOT] Error en temporizador de auto-expulsión:', err);
        }
    }, 30 * 1000);
}

// Initial settings load
loadSettings();

let connectionAttempts = 0;

async function start() {
    console.log('🤖 Iniciando Demonio de WhatsApp Moderador Avanzado...');
    
    // Obtener la versión de WhatsApp Web más reciente
    let version = [2, 3000, 1017539726]; // Fallback estable
    try {
        const { version: latestVersion } = await fetchLatestBaileysVersion();
        version = latestVersion;
        console.log(`[WA-BOT] Versión de WhatsApp Web detectada: ${version.join('.')}`);
    } catch (e) {
        console.log(`[WA-BOT] No se pudo obtener la versión actual de WA. Usando fallback: ${version.join('.')}`);
    }

    const { state, saveCreds } = await useMultiFileAuthState(AUTH_DIR);
    
    const sock = makeWASocket({
        version,
        auth: state,
        logger: pino({ level: 'silent' })
    });

    sock.ev.on('creds.update', saveCreds);

    sock.ev.on('connection.update', (update) => {
        const { connection, lastDisconnect } = update;
        
        if (connection === 'close') {
            const statusCode = lastDisconnect?.error?.output?.statusCode;
            const errorMsg = lastDisconnect?.error?.message || lastDisconnect?.error;
            console.log(`⚠️ Conexión cerrada. Código: ${statusCode}. Razón: ${errorMsg}`);
            
            // Si la sesión fue cerrada (loggedOut)
            const isLoggedOut = statusCode === DisconnectReason.loggedOut;
            if (isLoggedOut) {
                console.error('❌ La sesión de WhatsApp ha expirado o se ha cerrado permanentemente.');
                if (fs.existsSync(AUTH_DIR)) {
                    fs.rmSync(AUTH_DIR, { recursive: true, force: true });
                }
                process.exit(1);
            }

            connectionAttempts++;
            if (connectionAttempts > 5) {
                console.log('❌ Se detectaron múltiples fallos de conexión en el daemon bot.js.');
                console.log('Limpiando credenciales temporales corruptas para forzar reinicio limpio...');
                if (fs.existsSync(AUTH_DIR)) {
                    fs.rmSync(AUTH_DIR, { recursive: true, force: true });
                }
                connectionAttempts = 0;
                process.exit(1); // Detener para que systemd reinicie de forma limpia con QR nuevo
            }

            console.log('🔄 Reconectando en 5 segundos...');
            setTimeout(start, 5000);
        } else if (connection === 'open') {
            connectionAttempts = 0;
            console.log('✅ Bot de WhatsApp Moderador Avanzado listo y conectado.');
            // Iniciar timer
            startAutoKickTimer(sock);
        }
    });

    // Welcome messages and additions listener
    sock.ev.on('group-participants.update', async (update) => {
        try {
            const { id, participants, action } = update;
            
            // Refresh cache on any change
            getGroupMetadata(id, sock, true).catch(() => {});

            if (action === 'add') {
                const groupSet = getGroupSettings(id);
                const now = Date.now();
                const botJid = sock.user.id.split(':')[0] + '@s.whatsapp.net';

                for (const part of participants) {
                    if (part === botJid) continue; // Ignorar el bot

                    // Si es un moderador global del bot, ignorar reglas de presentación
                    if (settings.moderators && settings.moderators.includes(part)) continue;

                    // Añadir a colas
                    if (!groupSet.pendingWelcomes.includes(part)) {
                        groupSet.pendingWelcomes.push(part);
                    }
                    groupSet.pendingPresentations[part] = now;
                }
                saveSettings();

                console.log(`[WA-BOT] ${participants.length} usuarios añadidos. Cola de bienvenida actual: ${groupSet.pendingWelcomes.length}/5`);

                // Lanzar bienvenida si llegamos a 5
                if (groupSet.welcome_active && groupSet.pendingWelcomes.length >= 5) {
                    await sendBatchWelcome(id, sock);
                }
            }
        } catch (e) {
            console.error('[WA-BOT] Error en listener group-participants.update:', e);
        }
    });

    // Message events listener
    sock.ev.on('messages.upsert', async (m) => {
        if (m.type !== 'notify') return;

        for (const msg of m.messages) {
            try {
                if (!msg.message || msg.key.fromMe) continue;

            const chatJid = msg.key.remoteJid;
            const senderJid = msg.key.participant || msg.key.remoteJid;
            const isGroup = chatJid.endsWith('@g.us');

            if (!isGroup) continue;

            // Load JIDs limits
            let allowedGroups = [];
            try {
                if (fs.existsSync(GROUPS_FILE)) {
                    allowedGroups = JSON.parse(fs.readFileSync(GROUPS_FILE, 'utf8'));
                } else {
                    allowedGroups = ['all'];
                }
            } catch (e) {
                allowedGroups = ['all'];
            }

            const isAllowed = allowedGroups.includes('all') || allowedGroups.includes(chatJid);
            if (!isAllowed) continue;

            const text = getMessageText(msg.message).trim();
            const groupSet = getGroupSettings(chatJid);

            // 1. EVALUAR PRESENTACIÓN DE NUEVOS INTEGRANTES
            if (groupSet.pendingPresentations && groupSet.pendingPresentations[senderJid]) {
                if (isValidPresentation(text)) {
                    console.log(`[WA-BOT] Presentación aceptada de: ${senderJid} en ${chatJid}`);
                    delete groupSet.pendingPresentations[senderJid];
                    saveSettings();
                    
                    await sock.sendMessage(chatJid, {
                        text: `✅ @${senderJid.split('@')[0]} ¡Gracias por presentarte! Tus datos han sido validados con éxito. ¡Bienvenido/a formalmente!`,
                        mentions: [senderJid]
                    }, { quoted: msg });
                }
            }

            // 2. AUTOMACIÓN DE FILTRO (links / palabras)
            if (!text.startsWith('.')) {
                // Anti-links filter check (Solo si no es admin)
                if (groupSet.antilink) {
                    const hasLink = /https?:\/\/[^\s]+|www\.[^\s]+|wa\.me\/[0-9]+/i.test(text);
                    if (hasLink) {
                        const { isSenderAdmin, isBotAdmin } = await checkAdmins(chatJid, senderJid, sock);
                        if (!isSenderAdmin) {
                            if (isBotAdmin) {
                                // Delete link message
                                await sock.sendMessage(chatJid, { delete: msg.key });
                                
                                // Send warn message
                                await sock.sendMessage(chatJid, { 
                                    text: `⚠️ @${senderJid.split('@')[0]} los enlaces no están permitidos en este grupo y tu mensaje ha sido eliminado.`,
                                    mentions: [senderJid]
                                });
                            }
                            continue;
                        }
                    }
                }

                // Blacklisted Bad words check
                if (groupSet.badwords_active && groupSet.badwords && groupSet.badwords.length > 0) {
                    const lowerText = text.toLowerCase();
                    const hasBadWord = groupSet.badwords.some(word => lowerText.includes(word));
                    
                    if (hasBadWord) {
                        const { isSenderAdmin, isBotAdmin } = await checkAdmins(chatJid, senderJid, sock);
                        if (!isSenderAdmin) {
                            if (isBotAdmin) {
                                await sock.sendMessage(chatJid, { delete: msg.key });
                                await sock.sendMessage(chatJid, { 
                                    text: `⚠️ @${senderJid.split('@')[0]} tu mensaje ha sido eliminado debido a uso de vocabulario inapropiado.`,
                                    mentions: [senderJid]
                                });
                            }
                            continue;
                        }
                    }
                }
                continue;
            }

            // 3. COMANDOS DE PANEL (.help, .mute, .welcome, etc.)
            const parts = text.split(/\s+/);
            const cmd = parts[0].toLowerCase();

            // Comando .ping
            if (cmd === '.ping') {
                await sock.sendMessage(chatJid, { text: '🏓 *Pong!* El bot está activo y vigilando.' }, { quoted: msg });
                continue;
            }

            // Comando .help / .menu
            if (cmd === '.help' || cmd === '.menu') {
                const helpText = `🛡️ *MENÚ DE MODERACIÓN AVANZADA* 🤖\n` +
                                 `━━━━━━━━━━━━━━━━━━━━━━\n` +
                                 `🔒 *Anti-Links:* ${groupSet.antilink ? '✅ Activo' : '❌ Inactivo'}\n` +
                                 `📝 *Filtro Palabras:* ${groupSet.badwords_active ? '✅ Activo' : '❌ Inactivo'}\n` +
                                 `👋 *Mensaje Bienvenida:* ${groupSet.welcome_active ? '✅ Activo' : '❌ Inactivo'}\n` +
                                 `👥 *Cola Bienvenida:* \`${groupSet.pendingWelcomes.length}/5\` acumulados\n` +
                                 `━━━━━━━━━━━━━━━━━━━━━━\n` +
                                 `⚙️ *COMANDOS DE ADMINISTRADOR:*\n` +
                                 `• \`.mute\` : Cierra el grupo\n` +
                                 `• \`.unmute\` : Abre el grupo\n` +
                                 `• \`.kick @usuario\` : Expulsa miembro\n` +
                                 `• \`.pending\` : Listar pendientes de presentación\n` +
                                 `• \`.approve @usuario\` : Aprobación manual\n` +
                                 `• \`.mod add/remove/list\` : Gestionar moderadores del bot\n` +
                                 `• \`.antilink on/off\` : Auto-elimina links\n` +
                                 `• \`.badwords on/off/add/remove/list\`\n` +
                                 `• \`.welcome on/off/force\`\n` +
                                 `• \`.setwelcome <texto>\` : Configura bienvenida\n\n` +
                                 `ℹ️ *COMANDOS GENERALES:*\n` +
                                 `• \`.ping\` : Diagnóstico\n` +
                                 `━━━━━━━━━━━━━━━━━━━━━━`;
                await sock.sendMessage(chatJid, { text: helpText }, { quoted: msg });
                continue;
            }

            // Comando .mute
            if (cmd === '.mute') {
                const { isSenderAdmin, isBotAdmin } = await checkAdmins(chatJid, senderJid, sock);
                if (!isSenderAdmin) {
                    await sock.sendMessage(chatJid, { text: '❌ *Acceso Denegado:* Solo los administradores pueden usar este comando.' }, { quoted: msg });
                    continue;
                }
                if (!isBotAdmin) {
                    await sock.sendMessage(chatJid, { text: '❌ *Error:* El bot necesita ser administrador para cerrar el grupo.' }, { quoted: msg });
                    continue;
                }
                await sock.groupSettingUpdate(chatJid, 'announcement');
                await sock.sendMessage(chatJid, { text: '🔒 *Grupo cerrado:* Ahora solo los administradores pueden enviar mensajes.' }, { quoted: msg });
                continue;
            }

            // Comando .unmute
            if (cmd === '.unmute') {
                const { isSenderAdmin, isBotAdmin } = await checkAdmins(chatJid, senderJid, sock);
                if (!isSenderAdmin) {
                    await sock.sendMessage(chatJid, { text: '❌ *Acceso Denegado:* Solo los administradores pueden usar este comando.' }, { quoted: msg });
                    continue;
                }
                if (!isBotAdmin) {
                    await sock.sendMessage(chatJid, { text: '❌ *Error:* El bot necesita ser administrador para abrir el grupo.' }, { quoted: msg });
                    continue;
                }
                await sock.groupSettingUpdate(chatJid, 'not_announcement');
                await sock.sendMessage(chatJid, { text: '🔓 *Grupo abierto:* Ahora todos los miembros pueden enviar mensajes.' }, { quoted: msg });
                continue;
            }

            // Comando .kick
            if (cmd === '.kick') {
                const { isSenderAdmin, isBotAdmin } = await checkAdmins(chatJid, senderJid, sock);
                if (!isSenderAdmin) {
                    await sock.sendMessage(chatJid, { text: '❌ *Acceso Denegado:* Solo los administradores pueden usar este comando.' }, { quoted: msg });
                    continue;
                }
                if (!isBotAdmin) {
                    await sock.sendMessage(chatJid, { text: '❌ *Error:* El bot necesita ser administrador para expulsar miembros.' }, { quoted: msg });
                    continue;
                }
                const target = getTargetJid(msg, parts);
                if (!target) {
                    await sock.sendMessage(chatJid, { text: '⚠️ *Uso:* Escribe \`.kick @usuario\` o responde a su mensaje.' }, { quoted: msg });
                    continue;
                }
                const botJid = sock.user.id.split(':')[0] + '@s.whatsapp.net';
                if (target === botJid) {
                    await sock.sendMessage(chatJid, { text: '❌ No puedo auto-expulsarme del grupo.' }, { quoted: msg });
                    continue;
                }
                await sock.groupParticipantsUpdate(chatJid, [target], 'remove');
                await sock.sendMessage(chatJid, { text: `👋 @${target.split('@')[0]} ha sido expulsado del grupo por administración.`, mentions: [target] });
                
                // Limpiar de listas si existía
                if (groupSet.pendingPresentations && groupSet.pendingPresentations[target]) {
                    delete groupSet.pendingPresentations[target];
                    saveSettings();
                }
                continue;
            }

            // Comando .pending (Lista pendientes de presentación)
            if (cmd === '.pending') {
                const { isSenderAdmin } = await checkAdmins(chatJid, senderJid, sock);
                if (!isSenderAdmin) {
                    await sock.sendMessage(chatJid, { text: '❌ *Acceso Denegado:* Solo los administradores pueden usar este comando.' }, { quoted: msg });
                    continue;
                }
                const pendingJids = Object.keys(groupSet.pendingPresentations || {});
                if (pendingJids.length === 0) {
                    await sock.sendMessage(chatJid, { text: '📋 No hay usuarios pendientes de presentación.' }, { quoted: msg });
                    continue;
                }
                
                let textList = '📋 *INTEGRANTES PENDIENTES DE PRESENTACIÓN:*\n━━━━━━━━━━━━━━━━━━━━━━\n';
                const now = Date.now();
                for (const jid of pendingJids) {
                    const joinTime = groupSet.pendingPresentations[jid];
                    const elapsedMin = Math.floor((now - joinTime) / 60000);
                    const remainingMin = 60 - elapsedMin;
                    textList += `• @${jid.split('@')[0]} ➔ Restan *${remainingMin > 0 ? remainingMin : 0} minutos*\n`;
                }
                textList += '\n👉 Tienen 1 hora de plazo desde su ingreso para indicar: Nombre, País y Compañía.';
                textList += '\n━━━━━━━━━━━━━━━━━━━━━━';
                await sock.sendMessage(chatJid, { text: textList, mentions: pendingJids }, { quoted: msg });
                continue;
            }

            // Comando .approve @user (Aprobación manual)
            if (cmd === '.approve') {
                const { isSenderAdmin } = await checkAdmins(chatJid, senderJid, sock);
                if (!isSenderAdmin) {
                    await sock.sendMessage(chatJid, { text: '❌ *Acceso Denegado:* Solo los administradores pueden usar este comando.' }, { quoted: msg });
                    continue;
                }
                const target = getTargetJid(msg, parts);
                if (!target) {
                    await sock.sendMessage(chatJid, { text: '⚠️ *Uso:* Escribe \`.approve @usuario\` o responde a su mensaje.' }, { quoted: msg });
                    continue;
                }
                if (groupSet.pendingPresentations && groupSet.pendingPresentations[target]) {
                    delete groupSet.pendingPresentations[target];
                    saveSettings();
                    await sock.sendMessage(chatJid, { text: `✅ Presentación aprobada manualmente para @${target.split('@')[0]}.`, mentions: [target] }, { quoted: msg });
                } else {
                    await sock.sendMessage(chatJid, { text: `⚠️ El usuario @${target.split('@')[0]} no está en la lista de pendientes.`, mentions: [target] }, { quoted: msg });
                }
                continue;
            }

            // Comando .mod add/remove/list
            if (cmd === '.mod') {
                const { isSenderAdmin } = await checkAdmins(chatJid, senderJid, sock);
                if (!isSenderAdmin) {
                    await sock.sendMessage(chatJid, { text: '❌ *Acceso Denegado:* Solo los administradores pueden usar este comando.' }, { quoted: msg });
                    continue;
                }
                const action = parts[1];
                if (action === 'add') {
                    const rawNum = parts[2];
                    if (!rawNum) {
                        await sock.sendMessage(chatJid, { text: '⚠️ *Uso:* \`.mod add <número_teléfono>\` (ej: \`.mod add 5219999999999\`)' }, { quoted: msg });
                        continue;
                    }
                    const clean = rawNum.replace(/[^0-9]/g, '');
                    const target = `${clean}@s.whatsapp.net`;
                    
                    if (!settings.moderators) settings.moderators = [];
                    if (!settings.moderators.includes(target)) {
                        settings.moderators.push(target);
                        saveSettings();
                    }
                    await sock.sendMessage(chatJid, { text: `✅ @${clean} ha sido agregado a la lista de moderadores globales del bot.`, mentions: [target] }, { quoted: msg });
                } else if (action === 'remove' || action === 'del') {
                    const rawNum = parts[2];
                    if (!rawNum) {
                        await sock.sendMessage(chatJid, { text: '⚠️ *Uso:* \`.mod remove <número_teléfono>\` (ej: \`.mod remove 5219999999999\`)' }, { quoted: msg });
                        continue;
                    }
                    const clean = rawNum.replace(/[^0-9]/g, '');
                    const target = `${clean}@s.whatsapp.net`;
                    
                    if (!settings.moderators) settings.moderators = [];
                    const idx = settings.moderators.indexOf(target);
                    if (idx > -1) {
                        settings.moderators.splice(idx, 1);
                        saveSettings();
                        await sock.sendMessage(chatJid, { text: `✅ @${clean} ha sido removido de la lista de moderadores globales.`, mentions: [target] }, { quoted: msg });
                    } else {
                        await sock.sendMessage(chatJid, { text: `⚠️ El número @${clean} no está en la lista de moderadores.`, mentions: [target] }, { quoted: msg });
                    }
                } else if (action === 'list') {
                    const list = settings.moderators || [];
                    const mentions = [];
                    let textList = '📋 *MODERADORES GLOBALES DEL BOT:*\n━━━━━━━━━━━━━━━━━━━━━━\n';
                    if (list.length === 0) {
                        textList += '_Ninguno registrado (solo administradores nativos de WhatsApp)_';
                    } else {
                        list.forEach(jid => {
                            const num = jid.split('@')[0];
                            textList += `• @${num}\n`;
                            mentions.push(jid);
                        });
                    }
                    textList += '\n━━━━━━━━━━━━━━━━━━━━━━';
                    await sock.sendMessage(chatJid, { text: textList, mentions: mentions }, { quoted: msg });
                } else {
                    await sock.sendMessage(chatJid, { text: '⚠️ *Uso:* \n• \`.mod add <número>\`\n• \`.mod remove <número>\`\n• \`.mod list\`' }, { quoted: msg });
                }
                continue;
            }

            // Comando .antilink <on/off>
            if (cmd === '.antilink') {
                const { isSenderAdmin } = await checkAdmins(chatJid, senderJid, sock);
                if (!isSenderAdmin) {
                    await sock.sendMessage(chatJid, { text: '❌ *Acceso Denegado:* Solo los administradores pueden usar este comando.' }, { quoted: msg });
                    continue;
                }
                const opt = parts[1];
                if (opt === 'on') {
                    groupSet.antilink = true;
                    saveSettings();
                    await sock.sendMessage(chatJid, { text: '🛡️ *Filtro Anti-Links activado:* Los mensajes con links serán borrados automáticamente.' }, { quoted: msg });
                } else if (opt === 'off') {
                    groupSet.antilink = false;
                    saveSettings();
                    await sock.sendMessage(chatJid, { text: '⚠️ *Filtro Anti-Links desactivado.*' }, { quoted: msg });
                } else {
                    await sock.sendMessage(chatJid, { text: `⚠️ *Uso:* \`.antilink on\` o \`.antilink off\`\n*(Estado actual: ${groupSet.antilink ? 'Activado' : 'Desactivado'})*` }, { quoted: msg });
                }
                continue;
            }

            // Comando .badwords on/off/add/remove/list
            if (cmd === '.badwords') {
                const { isSenderAdmin } = await checkAdmins(chatJid, senderJid, sock);
                if (!isSenderAdmin) {
                    await sock.sendMessage(chatJid, { text: '❌ *Acceso Denegado:* Solo los administradores pueden usar este comando.' }, { quoted: msg });
                    continue;
                }
                const action = parts[1];
                if (action === 'on') {
                    groupSet.badwords_active = true;
                    saveSettings();
                    await sock.sendMessage(chatJid, { text: '🛡️ *Filtro de Palabras Prohibidas activado.*' }, { quoted: msg });
                } else if (action === 'off') {
                    groupSet.badwords_active = false;
                    saveSettings();
                    await sock.sendMessage(chatJid, { text: '⚠️ *Filtro de Palabras Prohibidas desactivado.*' }, { quoted: msg });
                } else if (action === 'add') {
                    const word = parts.slice(2).join(' ').trim().toLowerCase();
                    if (!word) {
                        await sock.sendMessage(chatJid, { text: '⚠️ *Uso:* \`.badwords add <palabra>\`' }, { quoted: msg });
                        continue;
                    }
                    if (!groupSet.badwords) groupSet.badwords = [];
                    if (!groupSet.badwords.includes(word)) {
                        groupSet.badwords.push(word);
                        saveSettings();
                    }
                    await sock.sendMessage(chatJid, { text: `✅ Palabra \`${word}\` añadida a la lista negra.` }, { quoted: msg });
                } else if (action === 'remove') {
                    const word = parts.slice(2).join(' ').trim().toLowerCase();
                    if (!word) {
                        await sock.sendMessage(chatJid, { text: '⚠️ *Uso:* \`.badwords remove <palabra>\`' }, { quoted: msg });
                        continue;
                    }
                    if (!groupSet.badwords) groupSet.badwords = [];
                    const idx = groupSet.badwords.indexOf(word);
                    if (idx > -1) {
                        groupSet.badwords.splice(idx, 1);
                        saveSettings();
                        await sock.sendMessage(chatJid, { text: `✅ Palabra \`${word}\` eliminada de la lista negra.` }, { quoted: msg });
                    } else {
                        await sock.sendMessage(chatJid, { text: `⚠️ La palabra \`${word}\` no está en la lista negra.` }, { quoted: msg });
                    }
                } else if (action === 'list') {
                    const list = groupSet.badwords || [];
                    await sock.sendMessage(chatJid, { text: `📋 *Palabras Prohibidas:* ${list.length > 0 ? list.map(w => `\`${w}\``).join(', ') : 'Ninguna registrada'}` }, { quoted: msg });
                } else {
                    await sock.sendMessage(chatJid, { text: `⚠️ *Uso:* \n• \`.badwords on/off\`\n• \`.badwords add <palabra>\`\n• \`.badwords remove <palabra>\`\n• \`.badwords list\`` }, { quoted: msg });
                }
                continue;
            }

            // Comando .welcome on/off/force
            if (cmd === '.welcome') {
                const { isSenderAdmin } = await checkAdmins(chatJid, senderJid, sock);
                if (!isSenderAdmin) {
                    await sock.sendMessage(chatJid, { text: '❌ *Acceso Denegado:* Solo los administradores pueden usar este comando.' }, { quoted: msg });
                    continue;
                }
                const opt = parts[1];
                if (opt === 'on') {
                    groupSet.welcome_active = true;
                    saveSettings();
                    await sock.sendMessage(chatJid, { text: '👋 *Mensajes de bienvenida activados.*' }, { quoted: msg });
                } else if (opt === 'off') {
                    groupSet.welcome_active = false;
                    saveSettings();
                    await sock.sendMessage(chatJid, { text: '⚠️ *Mensajes de bienvenida desactivados.*' }, { quoted: msg });
                } else if (opt === 'force' || opt === 'send') {
                    if (groupSet.pendingWelcomes.length === 0) {
                        await sock.sendMessage(chatJid, { text: '📋 No hay usuarios acumulados en la cola de bienvenida.' }, { quoted: msg });
                    } else {
                        await sock.sendMessage(chatJid, { text: `🔄 *Forzando bienvenida:* Enviando bienvenida a los ${groupSet.pendingWelcomes.length} usuarios acumulados...` }, { quoted: msg });
                        await sendBatchWelcome(chatJid, sock);
                    }
                } else {
                    await sock.sendMessage(chatJid, { text: `⚠️ *Uso:* \n• \`.welcome on\`\n• \`.welcome off\`\n• \`.welcome force\` (Envía la bienvenida actual a los acumulados, total: ${groupSet.pendingWelcomes.length})` }, { quoted: msg });
                }
                continue;
            }

            // Comando .setwelcome <texto>
            if (cmd === '.setwelcome') {
                const { isSenderAdmin } = await checkAdmins(chatJid, senderJid, sock);
                if (!isSenderAdmin) {
                    await sock.sendMessage(chatJid, { text: '❌ *Acceso Denegado:* Solo los administradores pueden usar este comando.' }, { quoted: msg });
                    continue;
                }
                const welcomeTxt = parts.slice(1).join(' ').trim();
                if (!welcomeTxt) {
                    await sock.sendMessage(chatJid, { text: '⚠️ Escribe el mensaje. Puedes usar \`{users}\` y \`{group}\` como variables.' }, { quoted: msg });
                    continue;
                }
                groupSet.welcome_message = welcomeTxt;
                saveSettings();
                await sock.sendMessage(chatJid, { text: `✅ *Mensaje de bienvenida establecido con éxito:* \n\n${welcomeTxt}` }, { quoted: msg });
                continue;
            } catch (e) {
                console.error('[WA-BOT] Error al procesar mensaje individual:', e);
            }
        }
    });
}

start().catch(err => {
    console.error('❌ Error fatal en el bot de WhatsApp:', err);
    process.exit(1);
});
