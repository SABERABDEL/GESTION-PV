# import_installateurs.py
from database import Database
import csv

def importer_installateurs():
    db = Database()
    
    with db.get_connection() as conn:
        cursor = conn.cursor()
        
        print("=" * 60)
        print("  IMPORT DES INSTALLATEURS")
        print("=" * 60)
        
        try:
            # Lire le fichier avec l'encodage approprié
            with open('INSTALLATEUR.txt', 'r', encoding='utf-8-sig') as f:
                lines = f.readlines()
            
            # Ignorer l'en-tête
            count = 0
            for i, line in enumerate(lines[1:]):
                if line.strip():
                    # Diviser par tabulation
                    parts = line.strip().split('\t')
                    if len(parts) >= 2:
                        nom = parts[0].strip()
                        code = parts[1].strip() if len(parts) > 1 else ''
                        
                        # Nettoyer les guillemets et espaces
                        nom = nom.replace('"', '').strip()
                        code = code.replace('"', '').strip()
                        
                        if nom and code:
                            cursor.execute('''
                                INSERT OR IGNORE INTO installateurs (nom, code) VALUES (?, ?)
                            ''', (nom, code))
                            if cursor.rowcount > 0:
                                count += 1
                                if count % 10 == 0:
                                    print(f"  ... {count} installateurs")
            
            conn.commit()
            print(f"\n✅ {count} installateurs importés")
            
            # Afficher les premiers pour vérifier
            cursor.execute("SELECT nom, code FROM installateurs ORDER BY nom LIMIT 10")
            print("\n📋 Premiers installateurs:")
            for nom, code in cursor.fetchall():
                print(f"   - {nom} (code: {code})")
            
        except Exception as e:
            print(f"❌ Erreur: {e}")
        
        print("=" * 60)

if __name__ == '__main__':
    importer_installateurs()