import sqlite3
from datetime import datetime
import subprocess

def load_chromecast_codes_from_db():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id, code, ip_address FROM chromecasts')
    codes = {row[1]: (row[0], row[2]) for row in cursor.fetchall()}
    conn.close()
    return codes

def verify_code_in_db(code, device_ip):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id, ip_address FROM chromecasts WHERE code = ?', (code,))
    chromecast = cursor.fetchone()

    if chromecast:
        chromecast_id, chromecast_ip = chromecast
        mac_address = get_mac_address(device_ip)
        pair_time = datetime.now()
        cursor.execute('''
            INSERT INTO pairs (chromecast_id, ip_address, mac_address, pair_time) VALUES (?, ?, ?, ?)
        ''', (chromecast_id, device_ip, mac_address, pair_time))
        conn.commit()
        conn.close()
        return True, chromecast_ip, cursor.lastrowid
    else:
        conn.close()
        return False, None, None

def get_mac_address(ip):
    try:
        result = subprocess.run(['arp', '-n', ip], capture_output=True, text=True)
        for line in result.stdout.splitlines():
            if ip in line:
                return line.split()[2]
    except Exception as e:
        print(f"Error retrieving MAC address for {ip}: {e}")
    return "00:00:00:00:00:00"
