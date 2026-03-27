# ajouter_clients.py
from database import Database
import random
import time

def ajouter_clients():
    db = Database()
    
    with db.get_connection() as conn:
        cursor = conn.cursor()
        
        print("=" * 60)
        print("  AJOUT DE 10291 CLIENTS")
        print("=" * 60)
        
        # Récupérer l'ID du district SFAX NORD
        cursor.execute("SELECT id FROM districts WHERE nom = 'SFAX NORD'")
        district = cursor.fetchone()
        
        if not district:
            print("❌ District SFAX NORD non trouvé!")
            return
        
        district_id = district[0]
        print(f"✅ District trouvé (ID: {district_id})")
        
        # Compter les clients existants
        cursor.execute("SELECT COUNT(*) FROM clients WHERE district_id = ?", (district_id,))
        count = cursor.fetchone()[0]
        print(f"📊 Clients existants: {count}")
        
        if count >= 10291:
            print("✅ Déjà 10291 clients")
            return
        
        # Clients de base
        premiers = [
            ('726466900', 'MOHAMED BEN SALAH', 'RTE TENIOUR KM6', '202', 6305, 'PROSOL', 'AVEC CREDIT'),
            ('726466901', 'AHMED SOKOR', 'RTE GREMDA KM4', '203', 4500, 'HORS PROSOL', 'SANS CREDIT'),
            ('726466902', 'FATMA CHAARI', 'RTE TENIOUR KM8', '204', 5200, 'PROSOL', 'AVEC CREDIT'),
            ('726466903', 'MOHAMED ALI', 'RTE GREMDA KM2', '207', 3800, 'HORS PROSOL', 'SANS CREDIT'),
            ('726466904', 'SALAH BEN NACEUR', 'RTE TENIOUR KM5', '210', 7100, 'PROSOL', 'AVEC CREDIT')
        ]
        
        for ref, nom, adr, code, conso, prog, cred in premiers:
            cursor.execute('''
                INSERT OR IGNORE INTO clients 
                (reference, nom, adresse, code_compteur, consommation, programme, credit, district_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (ref, nom, adr, code, conso, prog, cred, district_id))
            print(f"✅ Client {ref} ajouté")
        
        # Ajouter 10286 clients supplémentaires
        codes = ['202', '203', '204', '207', '210', '214', '222', '407', '410', '413']
        progs = ['PROSOL', 'HORS PROSOL']
        creds = ['AVEC CREDIT', 'SANS CREDIT']
        
        print("\n📊 Ajout des clients supplémentaires...")
        ajoutes = 5
        debut = time.time()
        
        for i in range(726466905, 726477196):
            ref = str(i)
            nom = f'CLIENT TEST {i}'
            adr = f'ADRESSE TEST {i}'
            code = random.choice(codes)
            conso = random.randint(3000, 8000)
            prog = random.choice(progs)
            cred = random.choice(creds)
            
            cursor.execute('''
                INSERT OR IGNORE INTO clients 
                (reference, nom, adresse, code_compteur, consommation, programme, credit, district_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (ref, nom, adr, code, conso, prog, cred, district_id))
            
            ajoutes += 1
            if ajoutes % 1000 == 0:
                print(f"  ... {ajoutes} clients ajoutés")
        
        conn.commit()
        
        # Vérifier le total
        cursor.execute("SELECT COUNT(*) FROM clients WHERE district_id = ?", (district_id,))
        total = cursor.fetchone()[0]
        
        fin = time.time()
        print(f"\n✅ {total} clients au total")
        print(f"⏱️  Temps: {fin - debut:.1f} secondes")
        print("=" * 60)

if __name__ == '__main__':
    ajouter_clients()