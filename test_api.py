# test_api.py
import requests

BASE = "http://127.0.0.1:5000"

print("1. Districts DRDSF:")
r = requests.get(f"{BASE}/api/districts/DRDSF")
print(r.json())
print()

print("2. Utilisateurs SFAX NORD:")
r = requests.get(f"{BASE}/api/utilisateurs/SFAX NORD")
print(r.json())
print()

print("3. Clients:")
r = requests.get(f"{BASE}/api/clients")
print(f"{len(r.json())} clients")