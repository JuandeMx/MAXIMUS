import sqlite3
import os
import subprocess

# RUTA CORRECTA DETECTADA
DB_PATHS = ['/etc/MaximusVpsMx/users.db', '/etc/MaximusVpsMx/hysteria_users.db']

# Lista de usuarios a restaurar
users_to_restore = [
    ("Juande", "mx", "2026-05-15"),
    ("Hugo", "123", "2026-05-24"),
    ("Juan", "123", "2026-05-24"),
    ("Andrea", "1234", "2026-05-25"),
    ("Oscar", "Paciencia", "2026-05-25"),
    ("Mario", "Cliente", "2026-05-26"),
    ("myreyna", "bella", "2026-05-26"),
    ("Ariel", "Byjuande", "2026-05-27"),
    ("prueba", "p1", "2026-05-10"),
    ("Prueba1", "Pruebacliente", "2026-05-05"),
    ("Clientemartes", "Martes", "2026-05-28"),
    ("Rooh", "Rooh1", "2026-05-28"),
    ("Sergio", "Cliente1", "2026-05-28"),
    ("Cliente-hija", "Hija10", "2026-05-28"),
    ("Pepito", "Buchaina", "2026-05-05"),
    ("Alberto", "Alberto1", "2026-05-29"),
    ("Juaquin", "Juaquin1", "2026-05-29"),
    ("Juaquin2", "Juaquin2", "2026-05-29"),
    ("Marcelo", "Marcelo", "2026-05-29"),
    ("Tiziano", "Tiziano", "2026-05-29"),
    ("Armando", "Armando", "2026-05-29"),
    ("Marcela", "Marcela", "2026-05-29"),
    ("Lauturo", "Lautaru", "2026-05-29"),
    ("Alfredo", "Alfredo", "2026-05-29"),
    ("Gogy2", "Gogy2", "2026-05-29"),
    ("Pedro", "Pedrogay", "2026-05-30"),
    ("Rodrigo", "ElAmerica", "2026-05-30"),
    ("Noconecta", "Tuhermana", "2026-05-30"),
    ("Luciana", "Arg", "2026-05-30"),
    ("Federico", "Cliente100", "2026-05-30"),
    ("Alex", "Alexcito", "2026-05-30"),
    ("Jhona", "Tortilla", "2026-05-30"),
    ("Luka", "Tvsmart", "2026-05-30"),
    ("Fernanda", "Yaestoyhastalamadre", "2026-05-30"),
    ("Facu", "Tomates", "2026-05-28"),
    ("Xiomara", "Claropersonal", "2026-05-30"),
    ("MIAMORSOTE_BELLA_CHULA_PRECIOSA", "TUFUTUROESPOSOBEBE", "2026-05-31"),
    ("Luis", "Luisitocomunica", "2026-05-31"),
    ("Abel", "Abel", "2026-05-31"),
    ("Pruebass", "Jsjs", "2026-05-08"),
    ("Mihermano", "Carlos", "2026-05-31"),
    ("JULIETA", "Tamarindo", "2026-05-31"),
    ("Prueba1dia", "Mex", "2026-05-08"),
    ("Brian", "Cliente", "2026-05-31"),
    ("Yoel", "Personal", "2026-06-01")
]

def restore():
    print("🚀 Restaurando usuarios en las bases de datos detectadas...")
    
    for db_path in DB_PATHS:
        print(f"\n📁 Procesando: {db_path}")
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Crear tabla si no existe
            cursor.execute('''CREATE TABLE IF NOT EXISTS users
                         (id INTEGER PRIMARY KEY AUTOINCREMENT,
                          username TEXT UNIQUE,
                          password TEXT,
                          expiry_date TEXT,
                          hwid TEXT DEFAULT 'OFF',
                          device_limit INTEGER DEFAULT 1)''')
            
            for user, password, expiry in users_to_restore:
                # Sistema (Solo una vez)
                if db_path == DB_PATHS[0]:
                    try:
                        subprocess.run(['userdel', '-f', user], stderr=subprocess.DEVNULL)
                        subprocess.run(['useradd', '-M', '-s', '/bin/false', user], check=True, stderr=subprocess.DEVNULL)
                        subprocess.run(['bash', '-c', f'echo "{user}:{password}" | chpasswd'], check=True)
                    except: pass

                # Base de Datos
                try:
                    cursor.execute("INSERT OR REPLACE INTO users (username, password, expiry_date, hwid, device_limit) VALUES (?, ?, ?, ?, ?)",
                                   (user, password, expiry, 'OFF', 1))
                except: pass
                    
            conn.commit()
            conn.close()
            print(f" ✅ Usuarios sincronizados en {db_path}")
        except Exception as e:
            print(f" ❌ Error en {db_path}: {e}")

    print("\n✅ ¡LISTO! Todos tus clientes han vuelto.")

if __name__ == "__main__":
    restore()
