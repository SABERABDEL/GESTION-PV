# import_codes_compteurs.py
from database import Database

def importer_codes_compteurs():
    db = Database()
    
    with db.get_connection() as conn:
        cursor = conn.cursor()
        
        print("=" * 60)
        print("  IMPORT DES CODES COMPTEURS")
        print("=" * 60)
        
        codes = [
            ('202', '2x10', '2,3', '2'),
            ('203', '2x15', '3,45', '3'),
            ('204', '2x20', '4,6', '4'),
            ('207', '2x32', '7,36', '6'),
            ('210', '2x45', '10,35', '6'),
            ('214', '2x63', '14,49', '6'),
            ('222', '2x100', '23', '6'),
            ('227', '2x125', '28,75', '6'),
            ('235', '2x160', '36,8', '6'),
            ('250', '2x225', '51,75', '6'),
            ('407', '4x10', '6,9', '6'),
            ('410', '4x15', '10,4', '9,5'),
            ('413', '4x20', '13,9', '13'),
            ('420', '4x30', '20,8', '20'),
            ('433', '4x50', '34,6', '33'),
            ('442', '4x63', '43,6', '42'),
            ('453', '4x80', '55,4', '53'),
            ('467', '4x100', '69,3', '67'),
            ('483', '4x125', '86,6', '83'),
            ('506', '4x160', '110,9', '106'),
            ('532', '4x200', '138,6', '132'),
            ('565', '4x250', '173,2', '165'),
            ('600', '4x300', '207,8', '200')
        ]
        
        count = 0
        for code, intensite, psouscrite, pmax in codes:
            cursor.execute('''
                INSERT OR IGNORE INTO codes_compteurs (code, intensite, psouscrite, pmax)
                VALUES (?, ?, ?, ?)
            ''', (code, intensite, psouscrite, pmax))
            if cursor.rowcount > 0:
                count += 1
                print(f"✅ Code {code} ajouté")
        
        conn.commit()
        print(f"\n✅ {count} codes compteurs importés")
        print("=" * 60)

if __name__ == '__main__':
    importer_codes_compteurs()