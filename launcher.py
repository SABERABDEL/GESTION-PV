#!/usr/bin/env python3
"""STEG PV - Lanceur"""
import sys, os, socket, webbrowser, threading, time, subprocess

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)
PORT = int(os.environ.get('STEG_PORT', 5000))
os.environ['STEG_PORT'] = str(PORT)

def is_port_free(port):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(0.5)
        s.connect(('127.0.0.1', port))
        s.close()
        return False
    except:
        return True

def get_all_ips():
    ips = []
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None):
            ip = info[4][0]
            if any(ip.startswith(p) for p in ('192.168.','10.','172.')):
                if ip not in ips: ips.append(ip)
    except: pass
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]; s.close()
        if ip not in ips: ips.append(ip)
    except: pass
    return ips

def open_firewall_silent(port):
    try:
        subprocess.run(['netsh','advfirewall','firewall','delete','rule','name=STEG_PV_HTTP'],
            capture_output=True, shell=True, timeout=5)
        r = subprocess.run(['netsh','advfirewall','firewall','add','rule',
            'name=STEG_PV_HTTP','dir=in','action=allow','protocol=TCP',
            f'localport={port}','profile=any'],
            capture_output=True, shell=True, timeout=5)
        return r.returncode == 0
    except: return False

def wait_and_open(url, port, max_wait=20):
    import urllib.request
    deadline = time.time() + max_wait
    while time.time() < deadline:
        try:
            urllib.request.urlopen(f'http://127.0.0.1:{port}', timeout=1)
            break
        except: time.sleep(0.5)
    try: webbrowser.open(url)
    except: pass

def main():
    sep = "=" * 58
    print(sep)
    print("   STEG PV - Gestion Photovoltaique")
    print(sep)

    # Verifier port libre (le .bat a deja tue l'ancien processus)
    if not is_port_free(PORT):
        print(f"\n[!]  Port {PORT} encore occupe.")
        print(f"     Fermez l'autre instance et relancez LANCER_STEG.vbs.")
        input("\nAppuyez sur une touche pour quitter...")
        return

    local_url = f"http://127.0.0.1:{PORT}"
    ips = get_all_ips()

    print(f"\n[OK] Port {PORT} libre - demarrage...")
    print(f"\n[LOCAL]  {local_url}")
    if ips:
        print(f"[RESEAU] Acces Android / autre PC:")
        for ip in ips:
            print(f"   http://{ip}:{PORT}")
        if open_firewall_silent(PORT):
            print(f"[OK]  Pare-feu: port {PORT} ouvert.")
        else:
            print(f"[!]   Pare-feu: Admin Global > Systeme > Acces Reseau")

    print(f"\n{sep}")
    print("   Gardez cette fenetre ouverte.")
    print("   Ctrl+C pour arreter.")
    print(sep)

    threading.Thread(target=wait_and_open, args=(local_url, PORT), daemon=True).start()

    os.chdir(BASE_DIR)
    from main import app
    try:
        app.run(host='0.0.0.0', port=PORT, debug=False, use_reloader=False)
    except (SystemExit, KeyboardInterrupt):
        print(f"\n{sep}\n   Serveur arrete normalement.\n{sep}")
    except OSError as e:
        if '10048' in str(e) or 'Address already' in str(e):
            print(f"\n[ERREUR] Port {PORT} occupe - fermez l'autre instance.")
        else:
            print(f"\n[ERREUR] {e}")
        input("Appuyez sur une touche...")
    except Exception as e:
        print(f"\n[ERREUR] {e}")
        input("Appuyez sur une touche...")

if __name__ == '__main__':
    main()
