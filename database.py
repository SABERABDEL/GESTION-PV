# database.py - STEG Gestion Photovoltaïque
import sqlite3
from datetime import datetime
import os, sys
from werkzeug.security import generate_password_hash, check_password_hash
from config import Config

def _get_base_dir():
    """Retourne le dossier de base (fonctionne PyInstaller + dev)"""
    if getattr(sys, 'frozen', False):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))

def _get_data_dir():
    """Retourne le dossier de données persistantes"""
    if getattr(sys, 'frozen', False):
        # À côté de l'exe
        return os.path.join(os.path.dirname(sys.executable), 'steg_data')
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')

class Database:
    def __init__(self, db_path=None):
        data_dir = _get_data_dir()
        os.makedirs(data_dir, exist_ok=True)
        self.db_path = db_path or os.path.join(data_dir, Config.DATABASE_NAME)
        self.bibliotheque_path = os.path.join(data_dir, 'bibliotheque.json')
        # Copier la bibliothèque depuis les ressources si absente
        bib_src = os.path.join(_get_base_dir(), 'data', 'bibliotheque.json')
        if not os.path.exists(self.bibliotheque_path) and os.path.exists(bib_src):
            import shutil
            shutil.copy2(bib_src, self.bibliotheque_path)
        self.init_database()
        self.migrer_base()

    def _init_or_migrate(self):
        """Réinitialise après changement de chemin (PyInstaller)"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        bib_src = os.path.join(_get_base_dir(), 'data', 'bibliotheque.json')
        if not os.path.exists(self.bibliotheque_path) and os.path.exists(bib_src):
            import shutil
            shutil.copy2(bib_src, self.bibliotheque_path)
        self.init_database()
        self.migrer_base()


    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    # ------------------------------------------------------------------
    # MIGRATION : ajoute les colonnes manquantes sur une DB existante
    # ------------------------------------------------------------------
    def migrer_base(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            # Récupérer les colonnes existantes de la table clients
            cursor.execute("PRAGMA table_info(clients)")
            cols_clients = {row[1] for row in cursor.fetchall()}

            nouvelles_colonnes_clients = [
                ("intensite",          "TEXT"),
                ("puissance_souscrite","TEXT"),
                ("pmax_pv",            "TEXT"),
                ("nb_modules",         "INTEGER DEFAULT 0"),
                ("puissance_element",  "INTEGER DEFAULT 250"),
                ("puissance_totale",   "INTEGER DEFAULT 0"),
                ("puissance_onduleur", "INTEGER DEFAULT 0"),
                ("installateur",       "TEXT DEFAULT ''"),
                ("installateur_code",  "TEXT"),
                ("type_opip",          "TEXT DEFAULT 'NOUVEAU'"),
                ("opip",               "TEXT"),
                ("date_depot",         "TEXT"),
                ("date_frais_dossier", "TEXT"),
                ("date_frais_ctr",     "TEXT"),
                ("approbation",        "TEXT DEFAULT 'NON'"),
                ("date_approbation",   "TEXT"),
                ("commentaires",       "TEXT"),
                ("date_modification",  "TEXT"),
            ]
            for col, typ in nouvelles_colonnes_clients:
                if col not in cols_clients:
                    try:
                        cursor.execute(f"ALTER TABLE clients ADD COLUMN {col} {typ}")
                        print(f"  Migration clients: +{col}")
                    except Exception as e:
                        print(f"  Migration clients SKIP {col}: {e}")

            # Table dossiers_techniques
            cursor.execute("PRAGMA table_info(dossiers_techniques)")
            cols_dt = {row[1] for row in cursor.fetchall()}
            # Créer si n'existe pas
            cursor.execute('''CREATE TABLE IF NOT EXISTS dossiers_techniques (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_id INTEGER NOT NULL, reference TEXT NOT NULL,
                date_reception_technique TEXT,
                etat_schema TEXT DEFAULT 'EN ATTENTE',
                etat_visite TEXT DEFAULT 'EN ATTENTE', date_visite TEXT,
                etat_rapport TEXT DEFAULT 'EN ATTENTE', date_rapport TEXT,
                avis_technique TEXT DEFAULT 'EN ATTENTE', date_avis TEXT,
                observations TEXT, agent_technique TEXT,
                district_id INTEGER,
                date_creation TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                date_modification TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (client_id) REFERENCES clients(id),
                FOREIGN KEY (district_id) REFERENCES districts(id))''')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_dt_client_id ON dossiers_techniques(client_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_dt_district_id ON dossiers_techniques(district_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_dt_reference ON dossiers_techniques(reference)')
            cursor.execute("PRAGMA table_info(dossiers_techniques)")
            cols_dt = {row[1] for row in cursor.fetchall()}
            if 'donnees_techniques' not in cols_dt:
                try:
                    cursor.execute("ALTER TABLE dossiers_techniques ADD COLUMN donnees_techniques TEXT")
                    print("  Migration dossiers_techniques: +donnees_techniques")
                except Exception as e:
                    print(f"  Migration DT skip: {e}")

            # Table demandes_compteurs
            cursor.execute('''CREATE TABLE IF NOT EXISTS demandes_compteurs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                reference TEXT NOT NULL,
                installateur TEXT, arrivage TEXT, police TEXT,
                date_paiement TEXT, numero_bon TEXT, type_compteur TEXT,
                remarque_district TEXT, remarque_labo TEXT, avis TEXT,
                date_reception_arrivage TEXT, date_envoi_arrivage TEXT,
                dispatching TEXT, date_approbation TEXT,
                date_reception_technique TEXT, date_pose TEXT, avis_reception TEXT,
                district_id INTEGER,
                date_creation TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                date_modification TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (district_id) REFERENCES districts(id)
            )''')

            # Migration: supprimer UNIQUE sur reference dans demandes_compteurs
            # (pour permettre plusieurs compteurs par référence)
            cursor.execute("PRAGMA index_list(demandes_compteurs)")
            indexes = cursor.fetchall()
            has_unique_ref = any('reference' in str(idx) for idx in indexes)
            if has_unique_ref:
                # Recréer la table sans contrainte UNIQUE
                cursor.execute("ALTER TABLE demandes_compteurs RENAME TO demandes_compteurs_old")
                cursor.execute('''CREATE TABLE demandes_compteurs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    reference TEXT NOT NULL,
                    installateur TEXT, arrivage TEXT, police TEXT,
                    date_paiement TEXT, numero_bon TEXT, type_compteur TEXT,
                    remarque_district TEXT, remarque_labo TEXT, avis TEXT,
                    date_reception_arrivage TEXT, date_envoi_arrivage TEXT,
                    dispatching TEXT, date_approbation TEXT,
                    date_reception_technique TEXT, date_pose TEXT, avis_reception TEXT,
                    district_id INTEGER,
                    date_creation TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    date_modification TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    date_demande_reception TEXT, agent_reception TEXT, agent_pose TEXT,
                    no_serie TEXT, reserves_reception TEXT,
                    FOREIGN KEY (district_id) REFERENCES districts(id))''')
                cursor.execute("INSERT INTO demandes_compteurs SELECT * FROM demandes_compteurs_old")
                cursor.execute("DROP TABLE demandes_compteurs_old")
                print("  Migration: UNIQUE supprimé sur demandes_compteurs.reference")

            # Migrations demandes_compteurs
            cursor.execute("PRAGMA table_info(demandes_compteurs)")
            cols_dc = {row[1] for row in cursor.fetchall()}
            for col, typ in [
                ("date_demande_reception", "TEXT"),
                ("agent_reception", "TEXT"),
                ("agent_pose", "TEXT"),
                ("no_serie", "TEXT"),
                ("reserves_reception", "TEXT"),
            ]:
                if col not in cols_dc:
                    try:
                        cursor.execute(f"ALTER TABLE demandes_compteurs ADD COLUMN {col} {typ}")
                        print(f"  Migration demandes_compteurs: +{col}")
                    except Exception as e:
                        print(f"  Migration DC skip {col}: {e}")

            # Supprimer les districts en double (garder le premier par nom+region_id)
            cursor.execute('''
                DELETE FROM districts WHERE id NOT IN (
                    SELECT MIN(id) FROM districts GROUP BY nom, region_id
                )
            ''')

            # Rôle SUPER_ADMIN
            cursor.execute("INSERT OR IGNORE INTO roles (code, nom) VALUES ('SUPER_ADMIN', 'Super Administrateur')")
            # Super admin global
            cursor.execute("SELECT id FROM roles WHERE code='SUPER_ADMIN'")
            r_sa = cursor.fetchone()
            if r_sa:
                cursor.execute("SELECT id, password FROM utilisateurs WHERE username='superadmin'")
                existing_sa = cursor.fetchone()
                import hashlib as _hlib2
                _sa_md5 = _hlib2.md5('123'.encode()).hexdigest()
                if existing_sa and existing_sa[1] != _sa_md5:
                    # Corriger le hash si différent (ex: ancien hash Werkzeug)
                    cursor.execute("UPDATE utilisateurs SET password=? WHERE username='superadmin'", (_sa_md5,))
                if not existing_sa:
                    import hashlib as _hlib
                    pwd_sa = _hlib.md5('123'.encode()).hexdigest()
                    cursor.execute("""INSERT OR IGNORE INTO utilisateurs
                        (nom, prenom, username, password, role_id, district_id, region_id, actif, autorisations)
                        VALUES ('ADMIN','SUPER','superadmin',?,?,NULL,NULL,1,
                        'commercial,technique,compteurs,reception,planning,bibliotheque,statistiques,import,admin,superadmin')
                    """, (pwd_sa, r_sa[0]))
            conn.commit()

    # ------------------------------------------------------------------
    # INITIALISATION DES TABLES
    # ------------------------------------------------------------------
    def init_database(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''CREATE TABLE IF NOT EXISTS regions (
                id INTEGER PRIMARY KEY AUTOINCREMENT, code TEXT UNIQUE NOT NULL, nom TEXT NOT NULL)''')
            # UNIQUE(nom, region_id) empêche les doublons à chaque redémarrage
            cursor.execute('''CREATE TABLE IF NOT EXISTS districts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                region_id INTEGER NOT NULL, nom TEXT NOT NULL, uf TEXT,
                UNIQUE(nom, region_id),
                FOREIGN KEY (region_id) REFERENCES regions(id))''')
            cursor.execute('''CREATE TABLE IF NOT EXISTS roles (
                id INTEGER PRIMARY KEY AUTOINCREMENT, code TEXT UNIQUE NOT NULL, nom TEXT NOT NULL)''')
            cursor.execute('''CREATE TABLE IF NOT EXISTS utilisateurs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nom TEXT NOT NULL, prenom TEXT NOT NULL,
                username TEXT UNIQUE NOT NULL, password TEXT NOT NULL,
                matricule TEXT UNIQUE, district_id INTEGER, role_id INTEGER, actif INTEGER DEFAULT 1,
                telephone TEXT DEFAULT \'\', autorisations TEXT DEFAULT \'\',
                FOREIGN KEY (district_id) REFERENCES districts(id),
                FOREIGN KEY (role_id) REFERENCES roles(id))''')
            for _cd in [("telephone","TEXT DEFAULT ''"),("autorisations","TEXT DEFAULT ''"),("bib_tabs","TEXT DEFAULT ''"),("region_id","INTEGER"),("email","TEXT DEFAULT ''")]:
                try: cursor.execute(f"ALTER TABLE utilisateurs ADD COLUMN {_cd[0]} {_cd[1]}")
                except: pass
            cursor.execute('''CREATE TABLE IF NOT EXISTS installateurs (
                id INTEGER PRIMARY KEY AUTOINCREMENT, nom TEXT UNIQUE NOT NULL, code TEXT,
                telephone1 TEXT, telephone2 TEXT, fax TEXT, adresse TEXT, email TEXT,
                date_validation TEXT, remarque TEXT)''')
            cursor.execute('''CREATE TABLE IF NOT EXISTS codes_compteurs (
                id INTEGER PRIMARY KEY AUTOINCREMENT, code TEXT UNIQUE NOT NULL,
                intensite TEXT, psouscrite TEXT, pmax TEXT)''')
            cursor.execute('''CREATE TABLE IF NOT EXISTS clients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                reference TEXT UNIQUE NOT NULL,
                nom TEXT, adresse TEXT,
                code_compteur TEXT, intensite TEXT, puissance_souscrite TEXT, pmax_pv TEXT,
                consommation INTEGER,
                nb_modules INTEGER DEFAULT 0, puissance_element INTEGER DEFAULT 250,
                puissance_totale INTEGER DEFAULT 0, puissance_onduleur INTEGER DEFAULT 0,
                installateur TEXT, installateur_code TEXT,
                type_opip TEXT DEFAULT 'NOUVEAU', opip TEXT,
                date_depot TEXT, date_frais_dossier TEXT, date_frais_ctr TEXT,
                programme TEXT DEFAULT 'PROSOL', credit TEXT DEFAULT 'AVEC CREDIT',
                approbation TEXT DEFAULT 'NON', date_approbation TEXT,
                commentaires TEXT, district_id INTEGER,
                date_creation TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                date_modification TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (district_id) REFERENCES districts(id))''')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_clients_district_id ON clients(district_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_clients_reference ON clients(reference)')
            cursor.execute('''CREATE TABLE IF NOT EXISTS dossiers_techniques (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_id INTEGER NOT NULL, reference TEXT NOT NULL,
                date_reception_technique TEXT,
                etat_schema TEXT DEFAULT 'EN ATTENTE',
                etat_visite TEXT DEFAULT 'EN ATTENTE', date_visite TEXT,
                etat_rapport TEXT DEFAULT 'EN ATTENTE', date_rapport TEXT,
                avis_technique TEXT DEFAULT 'EN ATTENTE', date_avis TEXT,
                observations TEXT, agent_technique TEXT, district_id INTEGER,
                date_creation TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                date_modification TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (client_id) REFERENCES clients(id))''')
            cursor.execute('''CREATE TABLE IF NOT EXISTS demandes_compteurs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                reference TEXT NOT NULL,
                installateur TEXT, arrivage TEXT, police TEXT,
                date_paiement TEXT, numero_bon TEXT, type_compteur TEXT,
                remarque_district TEXT, remarque_labo TEXT, avis TEXT,
                date_reception_arrivage TEXT, date_envoi_arrivage TEXT,
                dispatching TEXT, date_approbation TEXT,
                date_reception_technique TEXT, date_pose TEXT, avis_reception TEXT,
                district_id INTEGER,
                date_creation TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                date_modification TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (district_id) REFERENCES districts(id))''')
            # Index pour accélérer les requêtes par district (10 000+ lignes)
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_clients_district ON clients(district_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_clients_reference ON clients(reference)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_dossiers_district ON dossiers_techniques(district_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_dossiers_reference ON dossiers_techniques(reference)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_demandes_district ON demandes_compteurs(district_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_demandes_reference ON demandes_compteurs(reference)')
            conn.commit()
            self.inserer_donnees_initiales()
            self.migrer_passwords_en_clair()

    # ------------------------------------------------------------------
    # DONNÉES INITIALES (INSERT OR IGNORE = idempotent)
    # ------------------------------------------------------------------
    def inserer_donnees_initiales(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            # Régions (UNIQUE sur code → pas de doublon)
            for code, nom in [('DRDSF','DIRECTION REGIONALE SFAX'),('DRDC','DIRECTION REGIONALE CENTRE'),
                               ('DRDN','DIRECTION REGIONALE NORD'),('DRDT','DIRECTION REGIONALE TUNIS')]:
                cursor.execute('INSERT OR IGNORE INTO regions (code, nom) VALUES (?, ?)', (code, nom))

            # Districts DRDSF (UNIQUE sur nom+region_id → pas de doublon)
            cursor.execute("SELECT id FROM regions WHERE code='DRDSF'")
            r = cursor.fetchone()
            if r:
                rid = r[0]
                for nom, uf in [('SFAX NORD','520'),('SFAX SUD','521'),('SFAX VILLE','522'),
                                  ('MAHRES','523'),('JEBENIANA','524')]:
                    cursor.execute('INSERT OR IGNORE INTO districts (nom, uf, region_id) VALUES (?, ?, ?)',
                                   (nom, uf, rid))

            # Rôles
            for code, nom in [('ADMIN','Administrateur'),('TECHNIQUE','Technicien'),('COMMERCIAL','Commercial')]:
                cursor.execute('INSERT OR IGNORE INTO roles (code, nom) VALUES (?, ?)', (code, nom))

            # Utilisateurs SFAX NORD
            cursor.execute("SELECT id FROM districts WHERE nom='SFAX NORD' LIMIT 1")
            row = cursor.fetchone()
            if not row:
                conn.commit(); return
            did = row[0]
            cursor.execute("SELECT id FROM roles WHERE code='ADMIN'");    adm = cursor.fetchone()[0]
            cursor.execute("SELECT id FROM roles WHERE code='TECHNIQUE'"); tec = cursor.fetchone()[0]
            import hashlib as _hl
            for nom, prenom, username, password, matricule, role_id in [
                ('SOKOR','AHMED','ahmed.sokor','202cb962ac59075b964b07152d234b70','70796',tec),
                ('Ben Naceur','ADEL','adel.bennaceur','202cb962ac59075b964b07152d234b70','61612',tec),
                ('Ben Abdallah','IHSEN','ihsen.benabdallah','202cb962ac59075b964b07152d234b70','61304',tec),
                ('Ghanmi','HELMI','helmi.ghanmi','202cb962ac59075b964b07152d234b70','62696',tec),
                ('Hammouda','RIADH','riadh.hammouda','202cb962ac59075b964b07152d234b70','57833',tec),
                ('KHALFALLAH','FAICAL','faical.khalfallah','202cb962ac59075b964b07152d234b70','60418',tec),
                ('Abdelkafi','SABER','saber.abdelkafi','202cb962ac59075b964b07152d234b70','60157',adm)]:
                cursor.execute(
                    'INSERT OR IGNORE INTO utilisateurs (nom,prenom,username,password,matricule,district_id,role_id) VALUES (?,?,?,?,?,?,?)',
                    (nom, prenom, username, password, matricule, did, role_id))
            conn.commit()

    def migrer_passwords_en_clair(self):
        """Hashe tous les mots de passe en clair (non MD5) au démarrage"""
        import hashlib as _hl
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT id, password FROM utilisateurs')
            rows = cursor.fetchall()
            for uid, pwd in rows:
                if not pwd: continue
                is_md5 = len(pwd) == 32 and all(x in '0123456789abcdef' for x in pwd.lower())
                if not is_md5:
                    new_hash = _hl.md5(pwd.encode()).hexdigest()
                    cursor.execute('UPDATE utilisateurs SET password=? WHERE id=?', (new_hash, uid))
            conn.commit()

    # ------------------------------------------------------------------
    # UTILITAIRES
    # ------------------------------------------------------------------
    def get_district_id_by_nom(self, district_nom):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM districts WHERE nom=? LIMIT 1", (district_nom,))
            row = cursor.fetchone()
            return row[0] if row else None

    def get_regions(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, code, nom FROM regions ORDER BY nom")
            return [{'id': r[0], 'code': r[1], 'nom': r[2]} for r in cursor.fetchall()]

    def get_districts_by_region_code(self, code_region):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM regions WHERE code=?", (code_region,))
            region = cursor.fetchone()
            if not region: return []
            # GROUP BY pour éliminer tout doublon résiduel
            cursor.execute(
                "SELECT nom, uf FROM districts WHERE region_id=? GROUP BY nom ORDER BY nom",
                (region[0],))
            return [{'nom': r[0], 'uf': r[1]} for r in cursor.fetchall()]

    def get_utilisateurs_by_district_nom(self, district_nom):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            # Prendre le premier district en cas de doublon résiduel
            cursor.execute("SELECT id FROM districts WHERE nom=? LIMIT 1", (district_nom,))
            district = cursor.fetchone()
            if not district: return []
            cursor.execute(
                "SELECT u.username,u.nom,u.prenom,r.code,u.matricule "
                "FROM utilisateurs u JOIN roles r ON u.role_id=r.id "
                "WHERE u.district_id=? AND u.actif=1 ORDER BY u.nom",
                (district[0],))
            return [{'username':r[0],'nom':r[1],'prenom':r[2],'role_code':r[3],
                     'role_nom':'Administrateur' if r[3]=='ADMIN' else 'Technicien' if r[3]=='TECHNIQUE' else 'Commercial',
                     'matricule':r[4]} for r in cursor.fetchall()]

    def get_all_roles(self):
        with self.get_connection() as conn:
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            c.execute("SELECT id, code, nom FROM roles ORDER BY id")
            return [dict(r) for r in c.fetchall()]

    def verifier_superadmin(self, username, password):
        with self.get_connection() as conn:
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            c.execute("""SELECT u.id, u.username, u.nom, u.prenom, u.matricule, u.password,
                           u.autorisations, r.code as role_code
                    FROM utilisateurs u JOIN roles r ON u.role_id=r.id
                    WHERE u.username=? AND r.code='SUPER_ADMIN' AND u.actif=1""",
                    (username,))
            row = c.fetchone()
            if row:
                import hashlib as _h
                pwd_hash_md5 = _h.md5(password.encode()).hexdigest()
                stored_pwd = row['password']
                if check_password_hash(stored_pwd, password) or stored_pwd == pwd_hash_md5 or stored_pwd == password:
                    return dict(row)
            return None

    def verifier_utilisateur_par_district(self, username, password, district_nom):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            # Vérifier d'abord si c'est un ADMIN (accès tous districts)
            cursor.execute(
                "SELECT u.id,u.nom,u.prenom,u.username,u.password,r.code,COALESCE(u.autorisations,''),u.district_id "
                "FROM utilisateurs u JOIN roles r ON u.role_id=r.id "
                "WHERE u.username=? AND u.actif=1",
                (username,))
            user = cursor.fetchone()
            if not user:
                return None
            
            # Vérification du mot de passe (supporte MD5 pour la transition et Werkzeug pour le futur)
            import hashlib as _hl
            pwd_hash_md5 = _hl.md5(password.encode()).hexdigest() if password else ''
            stored_pwd = user['password']
            
            if not (check_password_hash(stored_pwd, password) or stored_pwd == pwd_hash_md5 or stored_pwd == password):
                return None

            uid, nom, prenom, uname, _, role_code, autorisations, district_id = user
            # ADMIN : accès à tous les districts — on accepte n'importe quel district valide
            if role_code == 'ADMIN' or 'admin' in (autorisations or ''):
                cursor.execute("SELECT id FROM districts WHERE nom=? LIMIT 1", (district_nom,))
                dist_row = cursor.fetchone()
                if not dist_row:
                    return None
                actual_district = district_nom
            else:
                # Non-ADMIN : vérifier que l'utilisateur appartient bien à ce district
                cursor.execute("SELECT id,nom FROM districts WHERE id=? LIMIT 1", (district_id,))
                dist_row = cursor.fetchone()
                if not dist_row:
                    return None
                actual_district = dist_row[1]
                if actual_district != district_nom:
                    return None
            
            return {'id': uid, 'nom': nom, 'prenom': prenom,
                    'username': uname, 'role_code': role_code,
                    'district_nom': district_nom,
                    'autorisations': autorisations}

    # ------------------------------------------------------------------
    # CLIENTS (COMMERCIAL)
    # ------------------------------------------------------------------
    def get_clients_by_district(self, district_nom):
        did = self.get_district_id_by_nom(district_nom)
        if not did: return []
        with self.get_connection() as conn:
            cursor = conn.cursor()
            # Vérifier les colonnes disponibles
            cursor.execute("PRAGMA table_info(clients)")
            cols = {row[1] for row in cursor.fetchall()}
            has_souscrite = 'puissance_souscrite' in cols
            has_pmax     = 'pmax_pv' in cols

            if has_souscrite and has_pmax:
                cursor.execute(
                    "SELECT reference,nom,adresse,code_compteur,consommation,programme,credit,"
                    "approbation,installateur_code,opip,nb_modules,puissance_totale,date_approbation,"
                    "type_opip,date_depot,puissance_onduleur,puissance_element,"
                    "puissance_souscrite,pmax_pv "
                    "FROM clients WHERE district_id=? ORDER BY reference", (did,))
                rows = cursor.fetchall()
                # Récupérer la colonne installateur séparément si elle existe
                has_inst = 'installateur' in cols
                if has_inst:
                    cursor.execute('SELECT reference, COALESCE(installateur,\'\') FROM clients WHERE district_id=? ORDER BY reference', (did,))
                    inst_map = {r[0]: r[1] for r in cursor.fetchall()}
                else:
                    inst_map = {}
                return [{'reference':r[0],'nom':r[1],'adresse':r[2],'codeCompteur':r[3],
                         'consommation':r[4],'programme':r[5],'credit':r[6],'approbation':r[7],
                         'installateur':inst_map.get(r[0],'') or r[8] or '','installateurCode':r[8] or '','opip':r[9],'nbModules':r[10],
                         'puissanceTotale':r[11],'dateApprobation':r[12],'typeOpip':r[13],'dateDepot':r[14],
                         'puissance_onduleur':r[15],'puissance_element':r[16],
                         'puissanceSouscrite':r[17],'pmaxPV':r[18]}
                        for r in rows]
            else:
                # Fallback sans les colonnes optionnelles
                cursor.execute(
                    "SELECT reference,nom,adresse,code_compteur,consommation,programme,credit,"
                    "approbation,installateur_code,opip,nb_modules,puissance_totale,date_approbation,"
                    "type_opip,date_depot,puissance_onduleur,puissance_element "
                    "FROM clients WHERE district_id=? ORDER BY reference", (did,))
                rows2 = cursor.fetchall()
                has_inst2 = 'installateur' in cols
                if has_inst2:
                    cursor.execute('SELECT reference, COALESCE(installateur,\'\') FROM clients WHERE district_id=? ORDER BY reference', (did,))
                    inst_map2 = {r[0]: r[1] for r in cursor.fetchall()}
                else:
                    inst_map2 = {}
                return [{'reference':r[0],'nom':r[1],'adresse':r[2],'codeCompteur':r[3],
                         'consommation':r[4],'programme':r[5],'credit':r[6],'approbation':r[7],
                         'installateur':inst_map2.get(r[0],'') or r[8] or '','installateurCode':r[8] or '','opip':r[9],'nbModules':r[10],
                         'puissanceTotale':r[11],'dateApprobation':r[12],'typeOpip':r[13],'dateDepot':r[14],
                         'puissance_onduleur':r[15],'puissance_element':r[16],
                         'puissanceSouscrite':'','pmaxPV':''}
                        for r in rows2]

    def get_client_by_reference(self, reference):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM clients WHERE reference=?", (reference,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def sauvegarder_client(self, data, district_nom):
        did = self.get_district_id_by_nom(district_nom)
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        ref = data.get('reference','').strip()
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM clients WHERE reference=?", (ref,))
            if cursor.fetchone():
                cursor.execute(
                    "UPDATE clients SET nom=?,adresse=?,code_compteur=?,intensite=?,"
                    "puissance_souscrite=?,pmax_pv=?,consommation=?,nb_modules=?,"
                    "puissance_element=?,puissance_totale=?,puissance_onduleur=?,"
                    "installateur=?,installateur_code=?,type_opip=?,opip=?,"
                    "date_depot=?,date_frais_dossier=?,date_frais_ctr=?,"
                    "programme=?,credit=?,approbation=?,date_approbation=?,"
                    "commentaires=?,date_modification=? WHERE reference=?",
                    (data.get('nom'),data.get('adresse'),data.get('codeCompteur'),
                     data.get('intensite'),data.get('puissanceSouscrite'),data.get('pmaxPV'),
                     data.get('consommation'),data.get('nbModules'),data.get('puissanceElement'),
                     data.get('puissanceTotale'),data.get('puissanceOnduleur'),
                     data.get('installateur'),
                     data.get('installateurCode') or data.get('installateur'),
                     data.get('typeOpip','NOUVEAU'),data.get('opip'),
                     data.get('dateDepot'),data.get('dateFraisDossier'),data.get('dateFraisCTR'),
                     data.get('programme','PROSOL'),data.get('credit','AVEC CREDIT'),
                     data.get('approbation','NON'),data.get('dateApprobation'),
                     data.get('commentaires'),now,ref))
                conn.commit(); return 'updated'
            else:
                cursor.execute(
                    "INSERT INTO clients (reference,nom,adresse,code_compteur,intensite,"
                    "puissance_souscrite,pmax_pv,consommation,nb_modules,puissance_element,"
                    "puissance_totale,puissance_onduleur,installateur,installateur_code,"
                    "type_opip,opip,date_depot,date_frais_dossier,date_frais_ctr,"
                    "programme,credit,approbation,date_approbation,commentaires,"
                    "district_id,date_creation,date_modification) "
                    "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (ref,data.get('nom'),data.get('adresse'),data.get('codeCompteur'),
                     data.get('intensite'),data.get('puissanceSouscrite'),data.get('pmaxPV'),
                     data.get('consommation'),data.get('nbModules',0),data.get('puissanceElement',250),
                     data.get('puissanceTotale',0),data.get('puissanceOnduleur',0),
                     data.get('installateur'),
                     data.get('installateurCode') or data.get('installateur'),
                     data.get('typeOpip','NOUVEAU'),data.get('opip'),
                     data.get('dateDepot'),data.get('dateFraisDossier'),data.get('dateFraisCTR'),
                     data.get('programme','PROSOL'),data.get('credit','AVEC CREDIT'),
                     data.get('approbation','NON'),data.get('dateApprobation'),
                     data.get('commentaires'),did,now,now))
                conn.commit(); return 'created'

    def supprimer_client(self, reference):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM clients WHERE reference=?", (reference,))
            conn.commit(); return cursor.rowcount > 0

    def importer_clients_excel(self, rows_data, district_nom, overwrite=False):
        did = self.get_district_id_by_nom(district_nom)
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        importes = 0; ignores = 0
        with self.get_connection() as conn:
            cursor = conn.cursor()
            for data in rows_data:
                ref = data.get('reference','').strip()
                if not ref: continue
                inst = data.get('installateurCode','') or data.get('installateur','')
                cursor.execute("SELECT id FROM clients WHERE reference=?", (ref,))
                existing = cursor.fetchone()
                try:
                    if existing:
                        if overwrite:
                            cursor.execute(
                                "UPDATE clients SET nom=?,adresse=?,code_compteur=?,consommation=?,"
                                "nb_modules=?,puissance_element=?,puissance_onduleur=?,puissance_totale=?,"
                                "installateur_code=?,opip=?,type_opip=?,programme=?,credit=?,approbation=?,"
                                "date_modification=? WHERE reference=?",
                                (data.get('nom',''),data.get('adresse',''),data.get('codeCompteur','202'),
                                 data.get('consommation',0),data.get('nbModules',0),data.get('puissanceElement',250),
                                 data.get('puissanceOnduleur',0),data.get('puissanceTotale',0),
                                 inst,data.get('opip',''),data.get('typeOpip','NOUVEAU'),
                                 data.get('programme','PROSOL'),data.get('credit','AVEC CREDIT'),
                                 data.get('approbation','NON'),now,ref))
                            importes += 1
                        else:
                            ignores += 1; continue
                    else:
                        cursor.execute(
                            "INSERT INTO clients (reference,nom,adresse,code_compteur,consommation,"
                            "nb_modules,puissance_element,puissance_onduleur,puissance_totale,"
                            "installateur_code,opip,type_opip,programme,credit,approbation,"
                            "district_id,date_creation,date_modification) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                            (ref,data.get('nom',''),data.get('adresse',''),data.get('codeCompteur','202'),
                             data.get('consommation',0),data.get('nbModules',0),data.get('puissanceElement',250),
                             data.get('puissanceOnduleur',0),data.get('puissanceTotale',0),
                             inst,data.get('opip',''),data.get('typeOpip','NOUVEAU'),
                             data.get('programme','PROSOL'),data.get('credit','AVEC CREDIT'),
                             data.get('approbation','NON'),did,now,now))
                        importes += 1
                except Exception as e:
                    ignores += 1
            conn.commit()
        return {'importes': importes, 'ignores': ignores}

    def get_stats_district(self, district_nom):
        did = self.get_district_id_by_nom(district_nom)
        if not did:
            return {'total_clients':0,'approuves':0,'en_attente':0,'total_compteurs':0,'dossiers_techniques':0}
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM clients WHERE district_id=?", (did,))
            total = cursor.fetchone()[0]
            # Approbation peut être NULL ou 'NON' dans l'ancienne DB → compter tous sauf 'NON'
            cursor.execute(
                "SELECT COUNT(*) FROM clients WHERE district_id=? AND approbation='OUI'", (did,))
            approuves = cursor.fetchone()[0]
            cursor.execute(
                "SELECT COUNT(*) FROM clients WHERE district_id=? AND (approbation='NON' OR approbation IS NULL)", (did,))
            en_attente = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM demandes_compteurs WHERE district_id=?", (did,))
            compteurs = cursor.fetchone()[0]
            # Dossiers techniques déposés = ceux avec date_reception_technique renseignée
            cursor.execute(
                "SELECT COUNT(*) FROM dossiers_techniques "
                "WHERE district_id=? AND date_reception_technique IS NOT NULL AND TRIM(date_reception_technique)!=''",
                (did,))
            techniques = cursor.fetchone()[0]
            return {'total_clients':total,'approuves':approuves,'en_attente':en_attente,
                    'total_compteurs':compteurs,'dossiers_techniques':techniques}

    # ------------------------------------------------------------------
    # DOSSIERS TECHNIQUES
    # ------------------------------------------------------------------

    def get_dossier_technique_by_reference(self, reference):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT dt.reference, dt.etat_schema, dt.etat_visite, dt.etat_rapport, "
                "dt.avis_technique, dt.date_visite, dt.date_rapport, dt.date_avis, "
                "dt.observations, dt.agent_technique, dt.date_reception_technique, "
                "dt.donnees_techniques, "
                "c.nom, c.installateur_code, c.programme "
                "FROM dossiers_techniques dt JOIN clients c ON dt.client_id=c.id "
                "WHERE dt.reference=? LIMIT 1", (reference,))
            row = cursor.fetchone()
            if not row: return None
            return {
                'reference': row[0], 'etatSchema': row[1], 'etatVisite': row[2],
                'etatRapport': row[3], 'avisTechnique': row[4], 'dateVisite': row[5],
                'dateRapport': row[6], 'dateAvis': row[7], 'observations': row[8],
                'agentTechnique': row[9], 'dateReceptionTechnique': row[10],
                'donnees_techniques': row[11],
                'nomClient': row[12], 'installateur': row[13], 'programme': row[14]
            }

    def get_dossiers_techniques_by_district(self, district_nom):
        did = self.get_district_id_by_nom(district_nom)
        if not did: return []
        with self.get_connection() as conn:
            cursor = conn.cursor()
            # LEFT JOIN : retourne TOUS les clients du district
            # même ceux sans dossier_technique (dt.* sera NULL)
            cursor.execute(
                "SELECT c.reference, "
                "COALESCE(dt.etat_schema,'EN ATTENTE'), "
                "COALESCE(dt.etat_visite,'EN ATTENTE'), "
                "COALESCE(dt.etat_rapport,'EN ATTENTE'), "
                "COALESCE(dt.avis_technique,'EN ATTENTE'), "
                "dt.date_visite, dt.date_rapport, dt.date_avis, "
                "dt.observations, dt.agent_technique, dt.date_reception_technique, "
                "c.nom, c.installateur_code, c.programme "
                "FROM clients c "
                "LEFT JOIN dossiers_techniques dt ON dt.reference=c.reference "
                "WHERE c.district_id=? ORDER BY c.reference", (did,))
            return [{'reference':r[0],'etatSchema':r[1],'etatVisite':r[2],'etatRapport':r[3],
                     'avisTechnique':r[4],'dateVisite':r[5],'dateRapport':r[6],'dateAvis':r[7],
                     'observations':r[8],'agentTechnique':r[9],'dateReceptionTechnique':r[10],
                     'nomClient':r[11],'installateur':r[12],'programme':r[13]}
                    for r in cursor.fetchall()]

    def sauvegarder_dossier_technique(self, data, district_nom):
        did = self.get_district_id_by_nom(district_nom)
        ref = data.get('reference','').strip()
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM clients WHERE reference=?", (ref,))
            client = cursor.fetchone()
            if not client:
                return {'error': f'Client non trouvé pour la référence {ref}'}
            client_id = client[0]
            cursor.execute("SELECT id FROM dossiers_techniques WHERE reference=?", (ref,))
            if cursor.fetchone():
                cursor.execute(
                    "UPDATE dossiers_techniques SET etat_schema=?,etat_visite=?,date_visite=?,"
                    "etat_rapport=?,date_rapport=?,avis_technique=?,date_avis=?,observations=?,"
                    "agent_technique=?,date_reception_technique=?,donnees_techniques=?,date_modification=? WHERE reference=?",
                    (data.get('etatSchema','EN ATTENTE'),data.get('etatVisite','EN ATTENTE'),
                     data.get('dateVisite'),data.get('etatRapport','EN ATTENTE'),data.get('dateRapport'),
                     data.get('avisTechnique','EN ATTENTE'),data.get('dateAvis'),data.get('observations'),
                     data.get('agentTechnique'),data.get('dateReceptionTechnique'),
                     data.get('donnees_techniques'),now,ref))
                conn.commit(); return 'updated'
            else:
                cursor.execute(
                    "INSERT INTO dossiers_techniques (client_id,reference,etat_schema,etat_visite,"
                    "date_visite,etat_rapport,date_rapport,avis_technique,date_avis,observations,"
                    "agent_technique,date_reception_technique,donnees_techniques,district_id,date_creation,date_modification) "
                    "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (client_id,ref,data.get('etatSchema','EN ATTENTE'),data.get('etatVisite','EN ATTENTE'),
                     data.get('dateVisite'),data.get('etatRapport','EN ATTENTE'),data.get('dateRapport'),
                     data.get('avisTechnique','EN ATTENTE'),data.get('dateAvis'),data.get('observations'),
                     data.get('agentTechnique'),data.get('dateReceptionTechnique'),
                     data.get('donnees_techniques'),did,now,now))
                conn.commit(); return 'created'

    def supprimer_dossier_technique(self, reference):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM dossiers_techniques WHERE reference=?", (reference,))
            conn.commit(); return cursor.rowcount > 0

    # ------------------------------------------------------------------
    # DEMANDES COMPTEURS
    # ------------------------------------------------------------------
    def get_demandes_compteurs_by_district(self, district_nom):
        did = self.get_district_id_by_nom(district_nom)
        if not did: return []
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT reference,installateur,arrivage,police,date_paiement,numero_bon,"
                "type_compteur,remarque_district,remarque_labo,avis,"
                "date_reception_arrivage,date_envoi_arrivage,dispatching,date_approbation,"
                "date_reception_technique,date_pose,avis_reception,"
                "date_demande_reception,agent_reception,agent_pose,no_serie,reserves_reception "
                "FROM demandes_compteurs WHERE district_id=? ORDER BY reference", (did,))
            return [{'reference':r[0],'installateur':r[1],'arrivage':r[2],'police':r[3],
                     'datePaiement':r[4],'numeroBon':r[5],'typeCompteur':r[6],
                     'remarqueDistrict':r[7],'remarqueLabo':r[8],'avis':r[9],
                     'dateReceptionArrivage':r[10],'dateEnvoiArrivage':r[11],
                     'dispatching':r[12],'dateApprobation':r[13],
                     'dateReceptionTechnique':r[14],'datePose':r[15],'avisReception':r[16],
                     'dateDemadeReception':r[17],'agentReception':r[18],
                     'agentPose':r[19],'noSerie':r[20],'reservesReception':r[21]}
                    for r in cursor.fetchall()]

    def sauvegarder_demande_compteur(self, data, district_nom):
        did = self.get_district_id_by_nom(district_nom)
        ref = data.get('reference','').strip()
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM demandes_compteurs WHERE reference=?", (ref,))
            if cursor.fetchone():
                cursor.execute(
                    "UPDATE demandes_compteurs SET installateur=?,arrivage=?,police=?,"
                    "date_paiement=?,numero_bon=?,type_compteur=?,remarque_district=?,"
                    "remarque_labo=?,avis=?,date_reception_arrivage=?,date_envoi_arrivage=?,"
                    "dispatching=?,date_approbation=?,date_demande_reception=?,"
                    "date_pose=?,avis_reception=?,reserves_reception=?,"
                    "agent_reception=?,agent_pose=?,no_serie=?,"
                    "date_modification=? WHERE reference=?",
                    (data.get('installateur'),data.get('arrivage'),data.get('police'),
                     data.get('datePaiement'),data.get('numeroBon'),data.get('typeCompteur'),
                     data.get('remarqueDistrict'),data.get('remarqueLabo'),data.get('avis'),
                     data.get('dateReceptionArrivage'),data.get('dateEnvoiArrivage'),
                     data.get('dispatching'),data.get('dateApprobation'),
                     data.get('dateDemadeReception'),data.get('datePose'),
                     data.get('avisReception'),data.get('reservesReception'),
                     data.get('agentReception'),data.get('agentPose'),data.get('noSerie'),
                     now,ref))
                conn.commit(); return 'updated'
            else:
                cursor.execute(
                    "INSERT INTO demandes_compteurs (reference,installateur,arrivage,police,"
                    "date_paiement,numero_bon,type_compteur,remarque_district,remarque_labo,avis,"
                    "date_reception_arrivage,date_envoi_arrivage,dispatching,date_approbation,"
                    "date_demande_reception,date_pose,avis_reception,reserves_reception,"
                    "agent_reception,agent_pose,no_serie,"
                    "district_id,date_creation,date_modification) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (ref,data.get('installateur'),data.get('arrivage'),data.get('police'),
                     data.get('datePaiement'),data.get('numeroBon'),data.get('typeCompteur'),
                     data.get('remarqueDistrict'),data.get('remarqueLabo'),data.get('avis'),
                     data.get('dateReceptionArrivage'),data.get('dateEnvoiArrivage'),
                     data.get('dispatching'),data.get('dateApprobation'),
                     data.get('dateDemadeReception'),data.get('datePose'),
                     data.get('avisReception'),data.get('reservesReception'),
                     data.get('agentReception'),data.get('agentPose'),data.get('noSerie'),
                     did,now,now))
                conn.commit(); return 'created'

    def supprimer_demande_compteur(self, reference):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM demandes_compteurs WHERE reference=?", (reference,))
            conn.commit(); return cursor.rowcount > 0

    def importer_demandes_compteurs_excel(self, rows_data, district_nom):
        did = self.get_district_id_by_nom(district_nom)
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        importes = 0
        skipped_noref = 0
        errors = []

        # Conserver tous les doublons (même référence = plusieurs compteurs)
        rows_valides = []
        for data in rows_data:
            ref = str(data.get('reference','')).strip()
            if not ref or ref == 'None':
                skipped_noref += 1
                continue
            rows_valides.append((ref, data))

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM demandes_compteurs WHERE district_id=?", (did,))
            for ref, data in rows_valides:
                try:
                    cursor.execute(
                        "INSERT INTO demandes_compteurs (reference,installateur,arrivage,"
                        "police,date_paiement,numero_bon,type_compteur,remarque_district,remarque_labo,"
                        "avis,date_reception_arrivage,date_envoi_arrivage,dispatching,date_approbation,"
                        "date_reception_technique,date_pose,avis_reception,"
                        "date_demande_reception,agent_reception,agent_pose,no_serie,"
                        "district_id,date_creation,date_modification) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                        (ref, data.get('installateur',''), data.get('arrivage',''), data.get('police',''),
                         data.get('datePaiement',''), data.get('numeroBon',''), data.get('typeCompteur',''),
                         data.get('remarqueDistrict',''), data.get('remarqueLabo',''), data.get('avis',''),
                         data.get('dateReceptionArrivage',''), data.get('dateEnvoiArrivage',''),
                         data.get('dispatching',''), data.get('dateApprobation',''),
                         data.get('dateReceptionTechnique',''), data.get('datePose',''),
                         data.get('avisReception',''),
                         data.get('dateDemadeReception',''), data.get('agentReception',''),
                         data.get('agentPose',''), data.get('noSerie',''),
                         did, now, now))
                    importes += 1
                except Exception as e_imp:
                    errors.append(str(ref))
            conn.commit()
        doublons = len(rows_valides) - len(set(r for r,_ in rows_valides))

        return {
            'importes': importes,
            'total': len(rows_data),
            'uniques': len(set(r for r,_ in rows_valides)),
            'skipped_noref': skipped_noref,
            'doublons_excel': doublons,
            'errors': len(errors)
        }

    # ------------------------------------------------------------------
    # RÉFÉRENTIELS
    # ------------------------------------------------------------------
    def get_all_installateurs(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT nom, code FROM installateurs ORDER BY nom")
            return [{'nom': r[0], 'code': r[1]} for r in cursor.fetchall()]

    def get_all_codes_compteurs(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT code, intensite, psouscrite, pmax FROM codes_compteurs ORDER BY code")
            return [{'code': r[0], 'intensite': r[1], 'psouscrite': r[2], 'pmax': r[3]}
                    for r in cursor.fetchall()]

    # ------------------------------------------------------------------
    # AGENTS (utilisateurs du district)
    # ------------------------------------------------------------------
    def get_agents_by_district(self, district_nom):
        did = self.get_district_id_by_nom(district_nom)
        if not did: return []
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT username, nom, prenom, matricule FROM utilisateurs "
                "WHERE district_id=? AND actif=1 ORDER BY nom", (did,))
            return [{'username': r[0], 'nom': r[1], 'prenom': r[2],
                     'nom_complet': f"{r[2]} {r[1]}", 'matricule': r[3] or ''}
                    for r in cursor.fetchall()]

    # ------------------------------------------------------------------
    # BIBLIOTHÈQUE JSON (CRUD onduleurs, panneaux, câbles, agents, CTR)
    # ------------------------------------------------------------------
    def get_bibliotheque(self):
        import json
        path = self.bibliotheque_path
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {'onduleurs':[], 'panneaux':[], 'cables_dc':[], 'cables_ac':[], 'ctrs':[], 'installateurs':[], 'agents_terrain':[]}

    def sauvegarder_bibliotheque(self, data):
        import json
        path = self.bibliotheque_path
        bib = self.get_bibliotheque()
        # Fusionner
        for k in ['onduleurs', 'panneaux', 'cables_dc', 'cables_ac', 'ctrs', 'installateurs', 'agents_terrain']:
            if k in data:
                bib[k] = data[k]
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(bib, f, ensure_ascii=False, indent=2)
        return True

    # ------------------------------------------------------------------
    # SYNCHRONISATION TECHNIQUE → COMPTEURS
    # ------------------------------------------------------------------
    def sync_technique_to_compteur(self, reference, tech_data):
        """Reporte les données de réception technique dans demandes_compteurs"""
        now = __import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM demandes_compteurs WHERE reference=?", (reference,))
            if not cursor.fetchone(): return False
            fields, vals = [], []
            mapping = {
                'date_approbation_technique': 'date_approbation',
                'date_reception_technique': 'date_reception_technique',
                'rec_date': 'date_reception_technique',   # depuis onglet technique (col.T)
                'rec_date_demande': 'date_demande_reception',
                'rec_agent': 'agent_reception',
                'rec_date_pose': 'date_pose',
                'ctr_n_serie': 'no_serie',
                'rec_avis': 'avis_reception',
                'avis_reception': 'avis_reception',
                'date_pose': 'date_pose'
            }
            for src, dst in mapping.items():
                if tech_data.get(src):
                    fields.append(f"{dst}=?")
                    vals.append(tech_data[src])
            if not fields: return False
            vals.extend([now, reference])
            cursor.execute(
                f"UPDATE demandes_compteurs SET {','.join(fields)}, date_modification=? WHERE reference=?",
                vals)
            conn.commit()
            return True

    # ------------------------------------------------------------------
    # CLIENTS – liste légère pour selects
    # ------------------------------------------------------------------
    def get_clients_light_by_district(self, district_nom):
        did = self.get_district_id_by_nom(district_nom)
        if not did: return []
        with self.get_connection() as conn:
            cursor = conn.cursor()
            # CAST + ORDER BY CAST pour tri numérique côté DB
            cursor.execute(
                "SELECT reference, nom FROM clients WHERE district_id=? ORDER BY CAST(reference AS INTEGER), reference",
                (did,))
            rows = cursor.fetchall()
            return [{'reference': r[0], 'nom': r[1] or ''} for r in rows]
