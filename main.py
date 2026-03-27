# main.py - STEG Gestion Photovoltaïque
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from database import Database
import os
from config import Config

app = Flask(__name__)
app.config.from_object(Config)

db = Database()

def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            if request.is_json or request.path.startswith('/api/'):
                return jsonify({'error': 'Non connecté', 'redirect': '/login'}), 401
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def access_required(autorisation):
    """Vérifie que l'utilisateur a l'autorisation demandée"""
    from functools import wraps
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if 'user_id' not in session:
                if request.is_json or request.path.startswith('/api/'):
                    return jsonify({'error': 'Non connecté'}), 401
                return redirect(url_for('login'))
            auths = session.get('autorisations', [])
            if autorisation not in auths and 'admin' not in auths:
                if request.is_json or request.path.startswith('/api/'):
                    return jsonify({'error': f'Accès refusé : autorisation {autorisation} requise'}), 403
                return render_template('acces_interdit.html',
                    username=session.get('username'),
                    district=session.get('district'),
                    autorisation_requise=autorisation,
                    autorisations=auths), 403
            return f(*args, **kwargs)
        return decorated
    return decorator

# ==================== ERROR HANDLERS ====================
@app.errorhandler(404)
def page_not_found(e):
    return render_template('acces_interdit.html', 
        username=session.get('username'),
        district=session.get('district'),
        autorisation_requise='Page non trouvée',
        autorisations=session.get('autorisations', [])), 404

@app.errorhandler(500)
def internal_server_error(e):
    return jsonify({'error': 'Erreur interne du serveur'}), 500

# ==================== AUTH ====================

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        district = request.form.get('district')
        # Tentative super admin (sans district)
        user = None
        if username == 'superadmin' or district == '__SUPERADMIN__':
            user = db.verifier_superadmin(username, password)
            if user:
                session.permanent = True
                session['user_id'] = user['id']
                session['username'] = user['username']
                session['district'] = '__GLOBAL__'
                session['role'] = 'SUPER_ADMIN'
                session['nom_complet'] = f"{user['prenom']} {user['nom']}"
                session['autorisations'] = ['commercial','technique','compteurs','reception',
                    'planning','bibliotheque','statistiques','import','admin','superadmin']
                flash(f"Bienvenue Super Admin", 'success')
                return redirect(url_for('admin_global'))
            else:
                flash('Super Admin: identifiant ou mot de passe incorrect (superadmin / 123)', 'danger')
                regions = db.get_regions()
                return render_template('login_steg.html', regions=regions)
        else:
            user = db.verifier_utilisateur_par_district(username, password, district)
        if user and district != '__SUPERADMIN__':
            session.permanent = True
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['district'] = district
            session['role'] = user['role_code']
            session['nom_complet'] = f"{user['prenom']} {user['nom']}"
            # Stocker les autorisations en session (liste)
            raw_auths = user.get('autorisations') or ''
            auths = [a.strip() for a in raw_auths.split(',') if a.strip()]
            # ADMIN = toutes les autorisations
            if user['role_code'] == 'ADMIN' or 'admin' in auths:
                auths = ['commercial','technique','compteurs','reception',
                         'planning','bibliotheque','statistiques','import','admin']
            # Si aucune autorisation définie → appliquer par défaut selon le rôle
            elif not auths:
                ROLE_DEFAULT = {
                    'TECHNIQUE':    ['technique','reception','planning'],
                    'COMMERCIAL':   ['commercial'],
                    'RECEPTION':    ['reception','planning'],
                    'VERIFICATION': ['technique'],
                    'COMPTEUR':     ['compteurs','planning'],
                    'LECTURE':      [],
                }
                auths = ROLE_DEFAULT.get(user['role_code'], [])
            session['autorisations'] = auths
            flash(f"Bienvenue {user['prenom']} {user['nom']}", 'success')
            return redirect(url_for('dashboard'))
        elif not user:
            flash('Identifiants incorrects ou district non valide', 'danger')
    regions = db.get_regions()
    return render_template('login_steg.html', regions=regions)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/shutdown', methods=['POST'])
def shutdown():
    """Arrêt propre du serveur — accessible depuis la page login"""
    import threading, os, signal
    def _stop():
        import time; time.sleep(0.8)
        os.kill(os.getpid(), signal.SIGTERM)
    threading.Thread(target=_stop, daemon=True).start()
    session.clear()
    return jsonify({'ok': True, 'message': "Serveur en cours d'arret..."})

# ==================== DASHBOARD ====================

@app.route('/dashboard')
@login_required
def dashboard():
    stats = db.get_stats_district(session.get('district'))
    return render_template('dashboard_complet.html',
        username=session.get('username'),
        nom_complet=session.get('nom_complet'),
        district=session.get('district'),
        role=session.get('role'),
        autorisations=session.get('autorisations', []),
        stats=stats)

# ==================== PAGES ====================

@app.route('/commercial')
@login_required
@access_required('commercial')
def commercial():
    return render_template('commercial.html',
        username=session.get('username'),
        district=session.get('district'),
        role=session.get('role'))

@app.route('/technique')
@login_required
@access_required('technique')
def technique():
    return render_template('technique.html',
        username=session.get('username'),
        district=session.get('district'),
        role=session.get('role'))

@app.route('/laboratoire')
@login_required
@access_required('reception')
def laboratoire():
    return render_template('laboratoire.html',
        username=session.get('username'),
        district=session.get('district'),
        role=session.get('role'))

@app.route('/compteurs')
@login_required
@access_required('compteurs')
def compteurs():
    return render_template('compteurs.html',
        username=session.get('username'),
        district=session.get('district'),
        role=session.get('role'))

# ==================== API AUTH ====================

@app.route('/api/districts/<region_code>')
def api_districts(region_code):
    return jsonify(db.get_districts_by_region_code(region_code))

@app.route('/api/utilisateurs/<district_nom>')
def api_utilisateurs(district_nom):
    return jsonify(db.get_utilisateurs_by_district_nom(district_nom))

# ==================== API GESTION UTILISATEURS ====================

@app.route('/api/agents', methods=['GET'])
@login_required
def api_agents_list():
    """Liste tous les utilisateurs du district avec leurs autorisations"""
    import sqlite3 as _sq
    district = session.get('district')
    try:
        with db.get_connection() as conn:
            conn.row_factory = _sq.Row
            c = conn.cursor()
            did = db.get_district_id_by_nom(district)
            c.execute("""
                SELECT u.id, u.nom, u.prenom, u.username, u.matricule,
                       u.actif, r.code as role_code, r.nom as role_nom,
                       COALESCE(u.telephone,'') as telephone,
                       COALESCE(u.autorisations,'') as autorisations,
                       COALESCE(u.bib_tabs,'') as bib_tabs
                FROM utilisateurs u JOIN roles r ON u.role_id=r.id
                WHERE u.district_id=? ORDER BY u.nom, u.prenom
            """, (did,))
            rows = c.fetchall()
            return jsonify([dict(r) for r in rows])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/agent', methods=['POST'])
@login_required
def api_agent_save():
    """Créer ou modifier un utilisateur"""
    import sqlite3 as _sq
    from werkzeug.security import generate_password_hash
    data = request.get_json()
    district = session.get('district')
    try:
        with db.get_connection() as conn:
            conn.row_factory = _sq.Row
            c = conn.cursor()
            did = db.get_district_id_by_nom(district)
            # Trouver role_id
            c.execute("SELECT id FROM roles WHERE code=?", (data.get('role_code','TECHNIQUE'),))
            role_row = c.fetchone()
            role_id = role_row['id'] if role_row else 2
            # Mot de passe
            pwd_raw = data.get('password','').strip()
            autorisations = ','.join(data.get('autorisations', []))
            bib_tabs = ','.join(data.get('bib_tabs', []))
            tel = data.get('telephone','')
            agent_id = data.get('id')
            if agent_id:
                # Modification
                if pwd_raw:
                    pwd_hash = generate_password_hash(pwd_raw)
                    c.execute("""UPDATE utilisateurs SET nom=?,prenom=?,username=?,password=?,
                        matricule=?,role_id=?,actif=?,telephone=?,autorisations=?,bib_tabs=?
                        WHERE id=? AND district_id=?""",
                        (data['nom'],data.get('prenom',''),data['username'],pwd_hash,
                         data.get('matricule',''),role_id,1 if data.get('actif',True) else 0,
                         tel,autorisations,bib_tabs,agent_id,did))
                else:
                    c.execute("""UPDATE utilisateurs SET nom=?,prenom=?,username=?,
                        matricule=?,role_id=?,actif=?,telephone=?,autorisations=?,bib_tabs=?
                        WHERE id=? AND district_id=?""",
                        (data['nom'],data.get('prenom',''),data['username'],
                         data.get('matricule',''),role_id,1 if data.get('actif',True) else 0,
                         tel,autorisations,bib_tabs,agent_id,did))
                conn.commit()
                return jsonify({'status':'updated'})
            else:
                # Création
                if not pwd_raw:
                    return jsonify({'error':'Mot de passe obligatoire'}), 400
                pwd_hash = generate_password_hash(pwd_raw)
                c.execute("""INSERT INTO utilisateurs
                    (nom,prenom,username,password,matricule,district_id,role_id,actif,telephone,autorisations,bib_tabs)
                    VALUES (?,?,?,?,?,?,?,1,?,?,?)""",
                    (data['nom'],data.get('prenom',''),data['username'],pwd_hash,
                     data.get('matricule',''),did,role_id,tel,autorisations,bib_tabs))
                conn.commit()
                return jsonify({'status':'created','id':c.lastrowid})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/agent/<int:agent_id>', methods=['DELETE'])
@login_required
def api_agent_delete(agent_id):
    district = session.get('district')
    try:
        with db.get_connection() as conn:
            c = conn.cursor()
            did = db.get_district_id_by_nom(district)
            c.execute("DELETE FROM utilisateurs WHERE id=? AND district_id=?", (agent_id, did))
            conn.commit()
            return jsonify({'status':'deleted'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/mes_droits_bib', methods=['GET'])
@login_required
def api_mes_droits_bib():
    """Retourne les droits d'accès aux onglets bibliothèque de l'utilisateur connecté"""
    import sqlite3 as _sq
    role = session.get('role')
    auths = session.get('autorisations', [])
    # Admin a tous les droits
    if role == 'ADMIN' or 'admin' in auths:
        all_rights = [f"{t}_{a}" for t in ['ond','pan','cable','ctr','inst'] for a in ['voir','ajouter','modifier','supprimer']]
        return jsonify({'bib_tabs': all_rights})
    username = session.get('username')
    district = session.get('district')
    try:
        with db.get_connection() as conn:
            conn.row_factory = _sq.Row
            c = conn.cursor()
            did = db.get_district_id_by_nom(district)
            c.execute("SELECT COALESCE(bib_tabs,'') as bib_tabs FROM utilisateurs WHERE username=? AND district_id=?", (username, did))
            row = c.fetchone()
            bib_tabs = row['bib_tabs'].split(',') if row and row['bib_tabs'] else []
            return jsonify({'bib_tabs': [r for r in bib_tabs if r]})
    except Exception as e:
        return jsonify({'bib_tabs': [], 'error': str(e)})

# ==================== API STATISTIQUES ====================

@app.route('/statistiques')
@login_required
@access_required('statistiques')
def page_statistiques():
    import datetime as _dt
    now_year = _dt.datetime.now().year
    return render_template('statistiques.html',
        username=session.get('username'),
        nom_complet=session.get('nom_complet',''),
        district=session.get('district'),
        now_year=now_year,
        now_year_m1=now_year-1,
        now_year_m2=now_year-2)

@app.route('/api/statistiques')
@login_required
def api_statistiques():
    """Statistiques avancées par période pour le district"""
    import sqlite3 as _sq, json as _j, traceback as _tb
    district = session.get('district')
    date_debut = request.args.get('date_debut','')
    date_fin   = request.args.get('date_fin','')
    try:
        did = db.get_district_id_by_nom(district)
        if not did: return jsonify({'error':'District introuvable'}), 400
        with db.get_connection() as conn:
            conn.row_factory = _sq.Row
            c = conn.cursor()

            def qwhere(tbl, col_date):
                w = f"WHERE {tbl}.district_id=?"
                p = [did]
                if date_debut: w += f" AND {col_date}>=?"; p.append(date_debut)
                if date_fin:   w += f" AND {col_date}<=?"; p.append(date_fin)
                return w, p

            # ── 1. COMMERCIAL ──────────────────────────────────────────────────────
            # date_depot = col.O; fallback sur date_creation si vide
            # Filtre période: COALESCE(date_depot, date_creation)
            def q_com(extra=''):
                w = "WHERE district_id=?"
                p = [did]
                if date_debut:
                    w += " AND COALESCE(NULLIF(TRIM(date_depot),''), date_creation) >= ?"
                    p.append(date_debut)
                if date_fin:
                    w += " AND COALESCE(NULLIF(TRIM(date_depot),''), date_creation) <= ?"
                    p.append(date_fin)
                if extra: w += ' ' + extra
                return w, p

            w,p = q_com(); c.execute(f"SELECT COUNT(*) FROM clients {w}", p)
            com_deposes = c.fetchone()[0]

            w,p = q_com("AND opip IS NOT NULL AND TRIM(opip)!='' AND UPPER(TRIM(opip))!='ANNULE'")
            c.execute(f"SELECT COUNT(*) FROM clients {w}", p)
            com_approuves = c.fetchone()[0]

            w,p = q_com("AND date_frais_dossier IS NOT NULL AND TRIM(date_frais_dossier)!=''")
            c.execute(f"SELECT COUNT(*) FROM clients {w}", p)
            com_payes_dossier = c.fetchone()[0]

            w,p = q_com("AND date_frais_ctr IS NOT NULL AND TRIM(date_frais_ctr)!=''")
            c.execute(f"SELECT COUNT(*) FROM clients {w}", p)
            com_payes_ctr = c.fetchone()[0]

            # par programme (avec filtre période)
            w,p = q_com()
            c.execute(f"SELECT programme, COUNT(*) FROM clients {w} GROUP BY programme ORDER BY COUNT(*) DESC", p)
            com_par_prog = [{'programme':r[0] or 'N/A','count':r[1]} for r in c.fetchall()]

            # par installateur (top 10, avec filtre période)
            w,p = q_com()
            c.execute(f"SELECT installateur_code, COUNT(*) as n FROM clients {w} GROUP BY installateur_code ORDER BY n DESC LIMIT 10", p)
            com_par_inst = [{'installateur':r[0] or '—','count':r[1]} for r in c.fetchall()]

            # ── 2. DOSSIERS TECHNIQUES ─────────────────────────────────────────────
            # Tout depuis donnees_techniques JSON (col.R/S/T/U)
            # Déposé      = col.R date_reception_technique non vide, filtre période sur col.R
            # Demande rec  = col.S rec_date_demande non vide
            # Réceptionné  = col.T rec_date non vide
            # Posé         = col.U ctr_n_date non vide
            # Avis dossier = avis_doss JSON
            c.execute("""SELECT donnees_techniques, date_reception_technique
                FROM dossiers_techniques dt WHERE dt.district_id=?""", (did,))
            tech_total = 0
            tech_par_avis = {'RAS': 0, 'RÉSERVES': 0, 'REFUSÉ': 0, 'EN ATTENTE': 0}
            for row in c.fetchall():
                # Filtre période sur col.R (date_reception_technique = date dépôt dossier)
                date_depot_tech = (row[1] or '').strip()[:10]
                if not date_depot_tech: continue  # exclure sans date de dépôt
                if date_debut and date_depot_tech < date_debut: continue
                if date_fin   and date_depot_tech > date_fin:   continue
                try: tech = _j.loads(row[0] or '{}')
                except: tech = {}
                # tech_total = TOUS les dossiers déposés (date_reception_technique non vide)
                # Ne PAS filtrer sur ctr_n_date (le dossier reste déposé même si compteur posé)
                tech_total += 1
                avis = (tech.get('avis_doss') or '').strip().upper()
                if 'RAS' in avis or 'APPROUV' in avis:
                    tech_par_avis['RAS'] += 1
                elif 'RÉSERVE' in avis or 'RESERVE' in avis or 'CORRECT' in avis or 'A CORRIGER' in avis:
                    tech_par_avis['RÉSERVES'] += 1
                elif 'REJET' in avis or 'REFUS' in avis:
                    tech_par_avis['REFUSÉ'] += 1
                else:
                    tech_par_avis['EN ATTENTE'] += 1

            # ── 3. DEMANDES DE RÉCEPTION ──────────────────────────────────────────
            # Source: dossiers_techniques.donnees_techniques JSON
            # col.S = rec_date_demande  → date demande réception (critère existence + période)
            # col.T = rec_date          → date réception effective
            # col.U = ctr_n_date        → date pose compteur
            # col.AA= rec_avis          → avis réception (RAS / RÉSERVES)
            # MONO/TRI depuis code_compteur clients
            c.execute("""SELECT dt.donnees_techniques, cl.code_compteur
                FROM dossiers_techniques dt
                LEFT JOIN clients cl ON dt.reference = cl.reference
                WHERE dt.district_id=?""", (did,))
            dem_rec_total = dem_rec_receptionnes = dem_rec_non_rec = 0
            dem_rec_pose = dem_rec_non_pose = 0
            dem_rec_ras = dem_rec_res = 0
            dem_rec_mono = dem_rec_tri = 0
            for row in c.fetchall():
                try: tech = _j.loads(row[0] or '{}')
                except: tech = {}
                # col.S : demande réception déposée
                rec_date_demande = (tech.get('rec_date_demande') or '').strip()
                if not rec_date_demande: continue
                if date_debut and rec_date_demande < date_debut: continue
                if date_fin   and rec_date_demande > date_fin:   continue
                dem_rec_total += 1
                # col.T : date réception effective
                rec_date = (tech.get('rec_date') or '').strip()
                if rec_date: dem_rec_receptionnes += 1
                else:        dem_rec_non_rec += 1
                # col.U : compteur posé
                ctr_date = (tech.get('ctr_n_date') or '').strip()
                if ctr_date: dem_rec_pose += 1
                else:        dem_rec_non_pose += 1
                # col.AA : avis réception
                avis_rec = (tech.get('rec_avis') or '').strip().upper()
                if 'RAS' in avis_rec:   dem_rec_ras += 1
                elif 'RES' in avis_rec: dem_rec_res += 1
                # MONO / TRI depuis code_compteur
                code_ctr = str(row[1] or '202').strip()
                fd = int(code_ctr[0]) if code_ctr and code_ctr[0].isdigit() else 2
                if fd >= 4: dem_rec_tri += 1
                else:       dem_rec_mono += 1

            # ── 4. DEMANDES COMPTEURS (table demandes_compteurs) ──────────────────
            w,p = qwhere('dc','date_demande_reception')
            c.execute(f"""SELECT dc.avis_reception, dc.type_compteur, dc.date_pose,
                           cl.installateur_code, cl.puissance_totale
                    FROM demandes_compteurs dc
                    LEFT JOIN clients cl ON dc.reference=cl.reference
                    {w}""", p)
            cnt_total = cnt_ras = cnt_res = 0
            cnt_pose = cnt_non_pose = 0
            cnt_mono = cnt_tri = 0
            cpt_puiss_mono = cpt_puiss_tri = 0.0
            cpt_par_inst = {}
            pose_par_inst = {}
            for r in c.fetchall():
                cnt_total += 1
                av = (r[0] or '').strip().upper()
                if av == 'RAS': cnt_ras += 1
                elif 'RES' in av: cnt_res += 1
                tp = (r[1] or '').upper()
                if 'TRI' in tp: cnt_tri += 1
                else: cnt_mono += 1
                dp = (r[2] or '').strip()
                if dp: cnt_pose += 1
                else: cnt_non_pose += 1
                inst = r[3] or '—'
                cpt_par_inst[inst] = cpt_par_inst.get(inst,0)+1
                if dp: pose_par_inst[inst] = pose_par_inst.get(inst,0)+1
                try:
                    pv = float(r[4] or 0)
                    if 'TRI' in tp: cpt_puiss_tri += pv
                    else: cpt_puiss_mono += pv
                except: pass

            # ── 5. COMPTEURS POSÉS par période ──────────────────────────────────────
            # Source: dossiers_techniques.donnees_techniques → ctr_n_date (date pose compteur col.U)
            # Puissance: clients.nb_modules × clients.puissance_element
            c.execute("""
                SELECT dt.donnees_techniques, cl.installateur_code,
                       cl.nb_modules, cl.puissance_element, cl.code_compteur
                FROM dossiers_techniques dt
                LEFT JOIN clients cl ON dt.reference = cl.reference
                WHERE dt.district_id = ?
            """, (did,))
            pose_total = pose_mono = pose_tri = 0
            pose_puiss_mono = pose_puiss_tri = 0.0
            pose_inst = {}
            for r in c.fetchall():
                try: tech = _j.loads(r[0] or '{}')
                except: tech = {}
                # Date pose = ctr_n_date (col.U saisie dans page technique)
                # Fallback: rec_date_pose (champ réception technique)
                date_pose = (tech.get('ctr_n_date') or tech.get('rec_date_pose') or '').strip()
                if not date_pose: continue  # pas posé
                # Filtrer sur la période
                if date_debut and date_pose < date_debut: continue
                if date_fin   and date_pose > date_fin:   continue
                pose_total += 1
                # Type compteur (depuis code_compteur clients)
                code_ctr = str(r[4] or '202').strip()
                fd = int(code_ctr[0]) if code_ctr and code_ctr[0].isdigit() else 2
                tp = 'TRI' if fd >= 4 else 'MONO'
                # Puissance = nb_modules × puissance_element (Wc)
                pv = 0.0
                try: pv = float(r[2] or 0) * float(r[3] or 250)
                except: pass
                if 'TRI' in tp: pose_tri += 1; pose_puiss_tri += pv
                else: pose_mono += 1; pose_puiss_mono += pv
                inst = r[1] or '—'
                pose_inst[inst] = pose_inst.get(inst,0)+1

            # ── 6. TOP INSTALLATEURS par puissance PV (nb_modules × puissance_element) ──
            c.execute("""SELECT installateur_code,
                           SUM(CAST(nb_modules AS REAL) * CAST(COALESCE(NULLIF(puissance_element,''),250) AS REAL)) as pt,
                           COUNT(*) as n
                FROM clients WHERE district_id=?
                GROUP BY installateur_code ORDER BY pt DESC LIMIT 10""", (did,))
            puiss_par_inst = [{'installateur':r[0] or '—',
                                'puissance':round(float(r[1] or 0)/1000,2),
                                'count':r[2]} for r in c.fetchall()]

            # ── 7. STATISTIQUES PV STEG (8 indicateurs) ─────────────────────────────
            from datetime import datetime as _dt

            def _days(d1s, d2s):
                try:
                    return (_dt.strptime(d2s[:10],'%Y-%m-%d') - _dt.strptime(d1s[:10],'%Y-%m-%d')).days
                except: return None

            # Stat 1: demandes en instance (date_demande_reception non vide, date_pose vide)
            c.execute("""SELECT COUNT(*) FROM demandes_compteurs
                WHERE district_id=? AND TRIM(COALESCE(date_demande_reception,''))!=''
                AND TRIM(COALESCE(date_pose,''))=''
                AND (? = '' OR date_demande_reception <= ?)
            """, (did, date_fin or '', date_fin or '9999'))
            pv_instance = c.fetchone()[0]

            # Stat 2: nouvelles demandes à partir de date_debut
            c.execute("""SELECT COUNT(*) FROM demandes_compteurs
                WHERE district_id=? AND TRIM(COALESCE(date_demande_reception,''))!=''
                AND (? = '' OR date_demande_reception >= ?)
            """, (did, date_debut or '', date_debut or ''))
            pv_nouvelles = c.fetchone()[0]

            # Stat 3: demandes satisfaites (date_pose non vide)
            c.execute("""SELECT COUNT(*) FROM demandes_compteurs
                WHERE district_id=? AND TRIM(COALESCE(date_pose,''))!=''
            """, (did,))
            pv_satisfaites = c.fetchone()[0]

            # Stat 4: compteurs posés dans la période
            c.execute("""SELECT COUNT(*) FROM demandes_compteurs
                WHERE district_id=? AND TRIM(COALESCE(date_pose,''))!=''
                AND (? = '' OR date_pose >= ?)
                AND (? = '' OR date_pose <= ?)
            """, (did, date_debut or '', date_debut or '',
                     date_fin or '', date_fin or '9999'))
            pv_poses_periode = c.fetchone()[0]

            # Stat 5: délai moyen étude = avis_date(col.AC JSON) - date_reception_technique(col.R)
            c.execute("""SELECT dt.donnees_techniques, dt.date_reception_technique
                FROM dossiers_techniques dt
                WHERE dt.district_id=?
                AND TRIM(COALESCE(dt.date_reception_technique,''))!=''
            """, (did,))
            delais5 = []
            for row5 in c.fetchall():
                try:
                    t5 = _j.loads(row5[0] or '{}')
                    avis_date = (t5.get('avis_date') or '').strip()[:10]
                    col_r = (row5[1] or '').strip()[:10]
                    if not avis_date or not col_r: continue
                    if date_fin and avis_date > date_fin: continue
                    d = _days(col_r, avis_date)
                    if d is not None and d >= 0: delais5.append(d)
                except: pass
            pv_delai_etude = round(sum(delais5)/len(delais5), 1) if delais5 else None

            # Stat 6: délai moyen branchement = date_pose(U) - date_demande_reception(S)
            c.execute("""SELECT date_pose, date_demande_reception FROM demandes_compteurs
                WHERE district_id=? AND TRIM(COALESCE(date_pose,''))!=''
                AND TRIM(COALESCE(date_demande_reception,''))!=''
                AND (? = '' OR date_pose <= ?)
            """, (did, date_fin or '', date_fin or '9999'))
            delais6 = [d for d in (_days(r[1],r[0]) for r in c.fetchall()) if d is not None and d >= 0]
            pv_delai_branchement = round(sum(delais6)/len(delais6), 1) if delais6 else None

            # Stat 7: total dossiers traités = compteurs posés (tous)
            pv_dossiers_traites = pv_satisfaites

            # Stat 8: puissance totale crête (clients avec date_pose non vide)
            c.execute("""SELECT COALESCE(SUM(cl.puissance_totale),0)
                FROM clients cl JOIN demandes_compteurs dc ON cl.reference=dc.reference
                WHERE cl.district_id=? AND TRIM(COALESCE(dc.date_pose,''))!=''
            """, (did,))
            pv_puissance_kwc = round((c.fetchone()[0] or 0)/1000, 2)

            return jsonify({
                'periode': {'debut': date_debut, 'fin': date_fin},
                'pv_steg': {
                    'instance': pv_instance,
                    'nouvelles': pv_nouvelles,
                    'satisfaites': pv_satisfaites,
                    'poses_periode': pv_poses_periode,
                    'delai_etude': pv_delai_etude,
                    'delai_branchement': pv_delai_branchement,
                    'dossiers_traites': pv_dossiers_traites,
                    'puissance_kwc': pv_puissance_kwc,
                },
                'commercial': {
                    'deposes': com_deposes,
                    'approuves': com_approuves,
                    'payes_dossier': com_payes_dossier,
                    'payes_ctr': com_payes_ctr,
                    'par_programme': com_par_prog,
                    'par_installateur': com_par_inst,
                },
                'technique': {
                    'total': tech_total,
                    'par_avis': tech_par_avis,
                },
                'demandes_reception': {
                    'total': dem_rec_total,
                    'receptionnes': dem_rec_receptionnes,
                    'non_receptionnes': dem_rec_non_rec,
                    'compteur_pose': dem_rec_pose,
                    'compteur_non_pose': dem_rec_non_pose,
                    'ras': dem_rec_ras,
                    'reserves': dem_rec_res,
                    'mono': dem_rec_mono,
                    'tri': dem_rec_tri,
                },
                'compteurs': {
                    'total': cnt_total,
                    'ras': cnt_ras,
                    'reserves': cnt_res,
                    'mono': cnt_mono,
                    'tri': cnt_tri,
                    'poses': cnt_pose,
                    'non_poses': cnt_non_pose,
                    'par_installateur': [{'inst':k,'n':v} for k,v in sorted(cpt_par_inst.items(),key=lambda x:-x[1])[:10]],
                    'puissance_mono_kwc': round(cpt_puiss_mono/1000,2),
                    'puissance_tri_kwc': round(cpt_puiss_tri/1000,2),
                },
                'pose': {
                    'total': pose_total,
                    'mono': pose_mono,
                    'tri': pose_tri,
                    'puissance_mono_kwc': round(pose_puiss_mono/1000,2),
                    'puissance_tri_kwc': round(pose_puiss_tri/1000,2),
                    'par_installateur': [{'inst':k,'n':v} for k,v in sorted(pose_inst.items(),key=lambda x:-x[1])[:10]],
                },
                'puissance_pv': puiss_par_inst,
            })
    except Exception as e:
        return jsonify({'error': str(e), 'trace': __import__('traceback').format_exc()}), 500


# ==================== SUPER ADMIN GLOBAL ====================

def superadmin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get('role') != 'SUPER_ADMIN':
            return jsonify({'error': 'Accès réservé au Super Admin'}), 403
        return f(*args, **kwargs)
    return decorated

@app.route('/admin_global')
@login_required
def admin_global():
    if session.get('role') != 'SUPER_ADMIN':
        return redirect(url_for('dashboard'))
    regions = db.get_regions()
    roles = db.get_all_roles()
    return render_template('admin_global.html',
        username=session.get('username'),
        nom_complet=session.get('nom_complet',''),
        regions=regions, roles=roles)

# --- CRUD Régions ---
@app.route('/api/admin/regions', methods=['GET'])
@login_required
@superadmin_required
def api_admin_regions():
    return jsonify(db.get_regions())

@app.route('/api/admin/region', methods=['POST'])
@login_required
@superadmin_required
def api_admin_create_region():
    d = request.get_json()
    code = (d.get('code') or '').strip().upper()
    nom  = (d.get('nom') or '').strip().upper()
    if not code or not nom: return jsonify({'error': 'Code et nom requis'}), 400
    with db.get_connection() as conn:
        try:
            conn.execute("INSERT INTO regions (code, nom) VALUES (?,?)", (code, nom))
            conn.commit()
            return jsonify({'status': 'created'})
        except Exception as e:
            return jsonify({'error': str(e)}), 400

@app.route('/api/admin/region/<int:rid>', methods=['DELETE'])
@login_required
@superadmin_required
def api_admin_delete_region(rid):
    with db.get_connection() as conn:
        conn.execute("DELETE FROM districts WHERE region_id=?", (rid,))
        conn.execute("DELETE FROM regions WHERE id=?", (rid,))
        conn.commit()
    return jsonify({'status': 'deleted'})

# --- CRUD Districts ---
@app.route('/api/admin/districts/<int:region_id>', methods=['GET'])
@login_required
def api_admin_districts(region_id):
    with db.get_connection() as conn:
        conn.row_factory = __import__('sqlite3').Row
        c = conn.cursor()
        c.execute("SELECT * FROM districts WHERE region_id=? ORDER BY nom", (region_id,))
        return jsonify([dict(r) for r in c.fetchall()])

@app.route('/api/admin/district', methods=['POST'])
@login_required
@superadmin_required
def api_admin_create_district():
    d = request.get_json()
    nom = (d.get('nom') or '').strip().upper()
    uf  = (d.get('uf') or '').strip()
    rid = d.get('region_id')
    if not nom or not rid: return jsonify({'error': 'Nom et région requis'}), 400
    with db.get_connection() as conn:
        try:
            conn.execute("INSERT INTO districts (nom, uf, region_id) VALUES (?,?,?)", (nom, uf, rid))
            conn.commit()
            return jsonify({'status': 'created'})
        except Exception as e:
            return jsonify({'error': str(e)}), 400

@app.route('/api/admin/district/<int:did>', methods=['DELETE'])
@login_required
@superadmin_required
def api_admin_delete_district(did):
    with db.get_connection() as conn:
        conn.execute("DELETE FROM utilisateurs WHERE district_id=?", (did,))
        conn.execute("DELETE FROM districts WHERE id=?", (did,))
        conn.commit()
    return jsonify({'status': 'deleted'})

# --- CRUD Utilisateurs (admin) ---
@app.route('/api/admin/users/<int:district_id>', methods=['GET'])
@login_required
def api_admin_users(district_id):
    import sqlite3 as _sq
    with db.get_connection() as conn:
        conn.row_factory = _sq.Row
        c = conn.cursor()
        c.execute("""SELECT u.id, u.nom, u.prenom, u.username, u.matricule,
                        u.actif, u.autorisations, u.telephone,
                        COALESCE(u.email,'') as email,
                        r.code as role_code, r.nom as role_nom
                    FROM utilisateurs u JOIN roles r ON u.role_id=r.id
                    WHERE u.district_id=? ORDER BY u.nom""", (district_id,))
        return jsonify([dict(r) for r in c.fetchall()])

@app.route('/api/admin/user', methods=['POST'])
@login_required
@superadmin_required
def api_admin_create_user():
    from werkzeug.security import generate_password_hash
    d = request.get_json()
    nom      = (d.get('nom') or '').strip().upper()
    prenom   = (d.get('prenom') or '').strip().upper()
    username = (d.get('username') or '').strip().lower()
    password = (d.get('password') or '').strip()
    matricule= (d.get('matricule') or '').strip()
    district_id = d.get('district_id')
    role_code   = d.get('role_code', 'TECHNIQUE')
    autorisations = d.get('autorisations', '')
    telephone  = (d.get('telephone') or '').strip()
    email      = (d.get('email') or '').strip()
    if not nom or not username or not password or not district_id:
        return jsonify({'error': 'Champs obligatoires manquants'}), 400
    pwd_hash = generate_password_hash(password)
    with db.get_connection() as conn:
        conn.row_factory = __import__('sqlite3').Row
        c = conn.cursor()
        c.execute("SELECT id FROM roles WHERE code=?", (role_code,))
        role = c.fetchone()
        if not role: return jsonify({'error': 'Rôle inconnu'}), 400
        try:
            c.execute("""INSERT INTO utilisateurs
                (nom, prenom, username, password, matricule, district_id, role_id, actif, autorisations, telephone, email)
                VALUES (?,?,?,?,?,?,?,1,?,?,?)""",
                (nom, prenom, username, pwd_hash, matricule, district_id, role['id'], autorisations, telephone, email))
            conn.commit()
            return jsonify({'status': 'created', 'id': c.lastrowid})
        except Exception as e:
            return jsonify({'error': str(e)}), 400

@app.route('/api/admin/user/<int:uid>', methods=['PUT'])
@login_required
@superadmin_required
def api_admin_update_user(uid):
    from werkzeug.security import generate_password_hash
    d = request.get_json()
    with db.get_connection() as conn:
        conn.row_factory = __import__('sqlite3').Row
        c = conn.cursor()
        c.execute("SELECT id FROM roles WHERE code=?", (d.get('role_code','TECHNIQUE'),))
        role = c.fetchone()
        if not role: return jsonify({'error': 'Rôle inconnu'}), 400
        fields = ["nom=?","prenom=?","username=?","matricule=?","role_id=?","actif=?","autorisations=?","telephone=?","email=?"]
        vals   = [d.get('nom','').upper(), d.get('prenom','').upper(), d.get('username','').lower(),
                  d.get('matricule',''), role['id'], 1 if d.get('actif',True) else 0,
                  d.get('autorisations',''), d.get('telephone',''), d.get('email','')]
        if d.get('password'):
            fields.append("password=?")
            vals.append(generate_password_hash(d['password']))
        vals.append(uid)
        c.execute(f"UPDATE utilisateurs SET {','.join(fields)} WHERE id=?", vals)
        conn.commit()
    return jsonify({'status': 'updated'})

@app.route('/api/admin/user/<int:uid>', methods=['DELETE'])
@login_required
@superadmin_required
def api_admin_delete_user(uid):
    with db.get_connection() as conn:
        conn.execute("DELETE FROM utilisateurs WHERE id=?", (uid,))
        conn.commit()
    return jsonify({'status': 'deleted'})

@app.route('/api/admin/roles', methods=['GET'])
@login_required
def api_admin_roles():
    return jsonify(db.get_all_roles())

# ==================== API CLIENTS ====================

@app.route('/api/clients', methods=['GET'])
@login_required
def api_clients():
    from flask import make_response
    try:
        clients = db.get_clients_by_district(session.get('district'))
        resp = make_response(jsonify(clients))
        resp.headers['Cache-Control'] = 'private, max-age=120'
        return resp
    except Exception as e:
        import traceback
        print(f"[ERREUR] /api/clients: {e}")
        traceback.print_exc()
        return jsonify([]), 200

@app.route('/api/client/<reference>', methods=['GET'])
@login_required
def api_client_detail(reference):
    client = db.get_client_by_reference(reference)
    if client:
        return jsonify(client)
    return jsonify({'error': 'Client non trouvé'}), 404

@app.route('/api/client', methods=['POST'])
@login_required
def api_sauvegarder_client():
    data = request.get_json()
    if not data or not data.get('reference'):
        return jsonify({'error': 'Référence obligatoire'}), 400
    result = db.sauvegarder_client(data, session.get('district'))
    if isinstance(result, dict) and 'error' in result:
        return jsonify(result), 400
    return jsonify({'status': result, 'message': 'Client sauvegardé avec succès'})

@app.route('/api/client/<reference>', methods=['DELETE'])
@login_required
def api_supprimer_client(reference):
    if db.supprimer_client(reference):
        return jsonify({'status': 'deleted'})
    return jsonify({'error': 'Client non trouvé'}), 404

@app.route('/api/clients/importer', methods=['POST'])
@login_required
def api_importer_clients():
    data = request.get_json()
    if not data or 'rows' not in data:
        return jsonify({'error': 'Données manquantes'}), 400
    overwrite = data.get('overwrite', False)
    district = session.get('district')
    rows = data['rows']
    import json as _json

    did = db.get_district_id_by_nom(district)
    if not did:
        return jsonify({'error': 'District introuvable'}), 400

    from datetime import datetime as _dt
    import sqlite3 as _sql
    now = _dt.now().strftime('%Y-%m-%d %H:%M:%S')

    importes = 0; ignores = 0; tech_ok = 0; ctr_ok = 0

    replace_all = data.get('replace_all', False)

    with db.get_connection() as conn:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        cursor = conn.cursor()

        # Mode remplacement complet: marquer les refs importées pour cleanup final
        imported_refs = set()
        if replace_all:
            # Collecter toutes les refs de ce batch pour le cleanup
            for _r in rows:
                _ref = str(_r.get('reference','')).strip()
                if _ref: imported_refs.add(_ref)

        for r in rows:
            ref = str(r.get('reference', '')).strip()
            if not ref: continue
            inst = r.get('installateurCode','') or r.get('installateur','')
            pOnd = r.get('puissanceOnduleur', 0)
            if not isinstance(pOnd, (int, float)): pOnd = 0

            # ---- TABLE CLIENTS ----
            cursor.execute("SELECT id FROM clients WHERE reference=?", (ref,))
            existing = cursor.fetchone()
            # INSERT OR REPLACE garantit l'écrasement même si contrainte
            client_vals = (
                ref, r.get('nom',''), r.get('adresse',''), r.get('codeCompteur','202'),
                r.get('consommation',0), r.get('nbModules',0), r.get('puissanceElement',250),
                pOnd, r.get('puissanceTotale',0),
                inst, r.get('opip',''), r.get('typeOpip','NOUVEAU'),
                r.get('programme','PROSOL'), r.get('credit','AVEC CREDIT'),
                r.get('approbation','NON'),
                r.get('dateDepot',''), r.get('dateFraisDossier',''), r.get('dateFraisCTR',''),
                did, now, now
            )
            if existing:
                if overwrite:
                    cursor.execute(
                        "UPDATE clients SET nom=?,adresse=?,code_compteur=?,consommation=?,"
                        "nb_modules=?,puissance_element=?,puissance_onduleur=?,puissance_totale=?,"
                        "installateur_code=?,opip=?,type_opip=?,programme=?,credit=?,approbation=?,"
                        "date_depot=?,date_frais_dossier=?,date_frais_ctr=?,district_id=?,"
                        "date_creation=?,date_modification=? WHERE reference=?",
                        client_vals[1:] + (ref,))
                    importes += 1
                else:
                    ignores += 1
                    # Continuer vers dossiers_techniques et demandes_compteurs même sans écrasement
            else:
                cursor.execute(
                    "INSERT OR IGNORE INTO clients (reference,nom,adresse,code_compteur,consommation,"
                    "nb_modules,puissance_element,puissance_onduleur,puissance_totale,"
                    "installateur_code,opip,type_opip,programme,credit,approbation,"
                    "date_depot,date_frais_dossier,date_frais_ctr,"
                    "district_id,date_creation,date_modification) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    client_vals)
                importes += 1

            # get client_id
            cursor.execute("SELECT id FROM clients WHERE reference=?", (ref,))
            row_client = cursor.fetchone()
            if not row_client: continue
            client_id = row_client[0]

            # ---- TABLE DOSSIERS TECHNIQUES ----
            don_tech = r.get('donnees_techniques','')
            cursor.execute("SELECT id FROM dossiers_techniques WHERE reference=?", (ref,))
            if cursor.fetchone():
                cursor.execute(
                    "UPDATE dossiers_techniques SET date_reception_technique=?,donnees_techniques=?,date_modification=? WHERE reference=?",
                    (r.get('dateReceptionDossier',''), don_tech, now, ref))
            else:
                cursor.execute(
                    "INSERT INTO dossiers_techniques (client_id,reference,date_reception_technique,donnees_techniques,district_id,date_creation,date_modification) VALUES (?,?,?,?,?,?,?)",
                    (client_id, ref, r.get('dateReceptionDossier',''), don_tech, did, now, now))
            tech_ok += 1

            # ---- TABLE DEMANDES COMPTEURS ----
            # Créer/mettre à jour depuis les colonnes de l'import Excel
            inst_dc = r.get('installateurCode','') or r.get('installateur','')
            cursor.execute("SELECT id FROM demandes_compteurs WHERE reference=?", (ref,))
            existing_dc = cursor.fetchone()
            if existing_dc:
                if overwrite:
                        cursor.execute("""UPDATE demandes_compteurs SET
                            installateur=?,type_compteur=?,no_serie=?,
                            date_demande_reception=?,date_reception_technique=?,
                            date_pose=?,avis_reception=?,agent_reception=?,
                            date_approbation=?,reserves_reception=?,
                            date_modification=? WHERE reference=?""",
                            (inst_dc, r.get('typeCompteur','MONO'), r.get('noSerie',''),
                             r.get('dateDemadeReception',''), r.get('dateReceptionTechnique',''),
                             r.get('datePose',''), r.get('avisReception',''),
                             r.get('agentReception',''), r.get('dateApprobation',''),
                             r.get('reservesReception',''), now, ref))
                        ctr_ok += 1
                else:
                    cursor.execute("""INSERT INTO demandes_compteurs
                        (reference,installateur,type_compteur,no_serie,
                         date_demande_reception,date_reception_technique,
                         date_pose,avis_reception,agent_reception,
                         date_approbation,reserves_reception,
                         district_id,date_creation,date_modification)
                        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                        (ref, inst_dc, r.get('typeCompteur','MONO'), r.get('noSerie',''),
                         r.get('dateDemadeReception',''), r.get('dateReceptionTechnique',''),
                         r.get('datePose',''), r.get('avisReception',''),
                         r.get('agentReception',''), r.get('dateApprobation',''),
                         r.get('reservesReception',''),
                         did, now, now))
                    ctr_ok += 1

        conn.commit()

    # Cleanup: si replace_all, supprimer les clients du district non dans l'import
    if replace_all and imported_refs:
        with db.get_connection() as conn2:
            c2 = conn2.cursor()
            # Supprimer les clients qui ne sont PAS dans les refs importées
            placeholders = ','.join(['?' for _ in imported_refs])
            c2.execute(f"""DELETE FROM dossiers_techniques WHERE district_id=?
                AND reference NOT IN ({placeholders})""", (did, *imported_refs))
            c2.execute(f"""DELETE FROM demandes_compteurs WHERE district_id=?
                AND reference NOT IN ({placeholders})""", (did, *imported_refs))
            c2.execute(f"""DELETE FROM clients WHERE district_id=?
                AND reference NOT IN ({placeholders})""", (did, *imported_refs))
            deleted = c2.rowcount
            conn2.commit()
    else:
        deleted = 0

    return jsonify({'importes': importes, 'ignores': ignores,
                    'tech_importes': tech_ok, 'ctr_importes': ctr_ok,
                    'deleted': deleted if replace_all else 0})

# ==================== API TECHNIQUE ====================

@app.route('/api/dossiers_techniques', methods=['GET'])
@login_required
def api_dossiers_techniques():
    dossiers = db.get_dossiers_techniques_by_district(session.get('district'))
    return jsonify(dossiers)

@app.route('/api/dossier_technique', methods=['POST'])
@login_required
def api_sauvegarder_dossier_technique():
    data = request.get_json()
    if not data or not data.get('reference'):
        return jsonify({'error': 'Référence obligatoire'}), 400
    result = db.sauvegarder_dossier_technique(data, session.get('district'))
    if isinstance(result, dict) and 'error' in result:
        return jsonify(result), 400
    return jsonify({'status': result, 'message': 'Dossier technique sauvegardé'})

@app.route('/api/dossier_technique/<reference>', methods=['DELETE'])
@login_required
def api_supprimer_dossier_technique(reference):
    if db.supprimer_dossier_technique(reference):
        return jsonify({'status': 'deleted'})
    return jsonify({'error': 'Dossier non trouvé'}), 404

# ==================== API COMPTEURS ====================

@app.route('/api/demandes_compteurs', methods=['GET'])
@login_required
def api_demandes_compteurs():
    demandes = db.get_demandes_compteurs_by_district(session.get('district'))
    return jsonify(demandes)

@app.route('/api/demande_compteur', methods=['POST'])
@login_required
def api_sauvegarder_demande_compteur():
    data = request.get_json()
    if not data or not data.get('reference'):
        return jsonify({'error': 'Référence obligatoire'}), 400
    result = db.sauvegarder_demande_compteur(data, session.get('district'))
    if isinstance(result, dict) and 'error' in result:
        return jsonify(result), 400
    return jsonify({'status': result, 'message': 'Demande sauvegardée'})

@app.route('/api/demande_compteur/<reference>', methods=['GET'])
@login_required
def api_get_demande_compteur(reference):
    demandes = db.get_demandes_compteurs_by_district(session.get('district'))
    found = next((d for d in demandes if d['reference'] == reference), None)
    if found:
        return jsonify(found)
    return jsonify({'error': 'Non trouvée'}), 404

@app.route('/api/demande_compteur/<reference>', methods=['DELETE'])
@login_required
def api_supprimer_demande_compteur(reference):
    if db.supprimer_demande_compteur(reference):
        return jsonify({'status': 'deleted'})
    return jsonify({'error': 'Demande non trouvée'}), 404

@app.route('/api/demandes_compteurs/importer', methods=['POST'])
@login_required
def api_importer_demandes_compteurs():
    data = request.get_json()
    if not data or 'rows' not in data:
        return jsonify({'error': 'Données manquantes'}), 400
    result = db.importer_demandes_compteurs_excel(data['rows'], session.get('district'))
    return jsonify(result)

# ==================== API RÉFÉRENTIELS ====================

@app.route('/api/installateurs')
def api_installateurs():
    return jsonify(db.get_all_installateurs())

@app.route('/api/codes_compteurs')
def api_codes_compteurs():
    return jsonify(db.get_all_codes_compteurs())

@app.route('/api/stats')
@login_required
def api_stats():
    return jsonify(db.get_stats_district(session.get('district')))


# ==================== API BIBLIOTHÈQUE CRUD ====================

@app.route('/api/dossier_technique/<reference>', methods=['GET'])
@login_required
def api_get_dossier_technique(reference):
    dossier = db.get_dossier_technique_by_reference(reference)
    if not dossier:
        # Essayer de créer depuis les données client (import commercial)
        client = db.get_client_by_reference(reference)
        if not client:
            return jsonify({'error': 'Référence non trouvée'}), 404
        # Retourner un dossier vide avec les données client disponibles
        # Chercher donnees_techniques dans dossiers_techniques directement
        import json as _j
        with db.get_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT donnees_techniques, date_reception_technique FROM dossiers_techniques WHERE reference=?", (reference,))
            row = c.fetchone()
        if row:
            tech_data = row[0]
            date_rec = row[1]
        else:
            tech_data = None
            date_rec = None
        return jsonify({
            'reference': reference,
            'etatSchema': 'EN ATTENTE', 'etatVisite': 'EN ATTENTE',
            'etatRapport': 'EN ATTENTE', 'avisTechnique': 'EN ATTENTE',
            'dateVisite': None, 'dateRapport': None, 'dateAvis': None,
            'observations': None, 'agentTechnique': None,
            'dateReceptionTechnique': date_rec or dict(client).get('date_approbation'),
            'donnees_techniques': tech_data,
            'nomClient': dict(client).get('nom'), 
            'installateur': dict(client).get('installateur_code'),
            'programme': dict(client).get('programme')
        })
    return jsonify(dossier)


@app.route('/bibliotheques')
@login_required
@access_required('bibliotheque')
def page_bibliotheques():
    role = session.get('role')
    auths = session.get('autorisations', [])
    is_admin = role == 'ADMIN' or 'admin' in auths
    return render_template('bibliotheque.html',
        username=session.get('username'),
        nom_complet=session.get('nom_complet',''),
        district=session.get('district'),
        role=role,
        autorisations=auths,
        IS_ADMIN=is_admin)


@app.route('/api/bibliotheque/import_excel', methods=['POST'])
@login_required
def api_bibliotheque_import_excel():
    """Import Excel multi-feuilles dans la bibliothèque JSON — ÉCRASE les données existantes"""
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Données manquantes'}), 400

    bib = db.get_bibliotheque()
    counts = {}

    # Chaque feuille REMPLACE complètement la section correspondante
    if 'installateurs' in data:
        valid = [i for i in data['installateurs'] if i.get('nom')]
        bib['installateurs'] = valid
        counts['installateurs'] = len(valid)

    if 'onduleurs' in data:
        valid = [o for o in data['onduleurs'] if o.get('modele')]
        bib['onduleurs'] = valid
        counts['onduleurs'] = len(valid)

    if 'panneaux' in data:
        valid = [p for p in data['panneaux'] if p.get('modele')]
        bib['panneaux'] = valid
        counts['panneaux'] = len(valid)

    if 'cables_dc' in data:
        valid = [c for c in data['cables_dc'] if c.get('type')]
        bib['cables_dc'] = valid
        counts['cables_dc'] = len(valid)

    if 'cables_ac' in data:
        valid = [c for c in data['cables_ac'] if c.get('type')]
        bib['cables_ac'] = valid
        counts['cables_ac'] = len(valid)

    # ── Codes Compteurs → DB (REPLACE) ──
    if 'ctrs' in data:
        added = 0
        with db.get_connection() as conn:
            c = conn.cursor()
            # Vider la table puis réinsérer
            c.execute("DELETE FROM codes_compteurs")
            for ctr in data['ctrs']:
                if not ctr.get('code'): continue
                try:
                    c.execute(
                        "INSERT INTO codes_compteurs (code, intensite, psouscrite, pmax) VALUES (?,?,?,?)",
                        (str(ctr['code']).strip(),
                         str(ctr.get('intensite','')).strip(),
                         float(ctr.get('psouscrite') or 0),
                         float(ctr.get('pmax') or 0)))
                    added += 1
                except Exception as e_ctr:
                    pass
            conn.commit()
        counts['ctrs'] = added

    # ── Coefficients de correction (feuille autres) ──
    if 'fact_k' in data:
        bib['fact_k'] = data['fact_k']
        counts['fact_k'] = len(data['fact_k'])
    if 'uw_table' in data:
        bib['uw_table'] = data['uw_table']
        counts['uw_table'] = len(data['uw_table'])

    # ── Caractéristiques câbles et coefficients K (feuille Cable) ──
    for key in ['caract_cuivre','caract_alu','coef_k1','coef_k2','coef_k3']:
        if key in data:
            bib[key] = data[key]
            counts[key] = len(data[key])

    db.sauvegarder_bibliotheque(bib)
    return jsonify(counts)

@app.route('/api/bibliotheque', methods=['GET'])
def api_get_bibliotheque():
    from flask import make_response
    resp = make_response(jsonify(db.get_bibliotheque()))
    # Cache 5 minutes côté navigateur — évite rechargement à chaque page
    resp.headers['Cache-Control'] = 'private, max-age=300'
    return resp

@app.route('/api/bibliotheque', methods=['POST'])
@login_required
def api_save_bibliotheque():
    import sqlite3 as _sq
    data = request.get_json()
    if not data: return jsonify({'error': 'Données manquantes'}), 400
    db.sauvegarder_bibliotheque(data)
    # Synchroniser les installateurs de la bibliothèque → table SQLite installateurs
    if 'installateurs' in data:
        try:
            with db.get_connection() as conn:
                conn.row_factory = _sq.Row
                c = conn.cursor()
                for inst in data['installateurs']:
                    nom = (inst.get('nom') or '').strip()
                    if not nom: continue
                    code = (inst.get('code') or '').strip()
                    tel  = (inst.get('tel') or inst.get('telephone') or '').strip()
                    email= (inst.get('email') or '').strip()
                    adr  = (inst.get('adresse') or '').strip()
                    c.execute("""INSERT INTO installateurs(nom,code,telephone1,email,adresse)
                        VALUES(?,?,?,?,?)
                        ON CONFLICT(nom) DO UPDATE SET
                          code=excluded.code,
                          telephone1=excluded.telephone1,
                          email=excluded.email,
                          adresse=excluded.adresse""",
                        (nom, code, tel, email, adr))
                conn.commit()
        except Exception as e:
            pass  # ne pas bloquer si erreur de sync
    return jsonify({'status': 'saved'})

@app.route('/api/agents')
@login_required
def api_agents():
    agents = db.get_agents_by_district(session.get('district'))
    # Ajouter agents_terrain de la bibliothèque
    bib = db.get_bibliotheque()
    for a in bib.get('agents_terrain', []):
        nom = (a.get('nom') or a.get('name') or '').strip()
        prenom = (a.get('prenom') or '').strip()
        if nom or prenom:
            agents.append({'nom': nom, 'prenom': prenom, 'nom_complet': f"{prenom} {nom}".strip()})
    return jsonify(agents)

@app.route('/api/sync_manquants', methods=['POST'])
@login_required
def api_sync_manquants():
    """Crée les dossiers_techniques et demandes_compteurs manquants pour tous les clients du district."""
    from datetime import datetime as _dt
    district = session.get('district')
    did = db.get_district_id_by_nom(district)
    if not did:
        return jsonify({'error': 'District introuvable'}), 400
    now = _dt.now().strftime('%Y-%m-%d %H:%M:%S')
    tech_crees = 0; ctr_crees = 0
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, reference, installateur_code FROM clients WHERE district_id=?", (did,))
        clients = cursor.fetchall()
        for client_id, ref, inst in clients:
            # dossiers_techniques
            cursor.execute("SELECT id FROM dossiers_techniques WHERE reference=?", (ref,))
            if not cursor.fetchone():
                cursor.execute(
                    "INSERT INTO dossiers_techniques (client_id,reference,district_id,date_creation,date_modification) VALUES (?,?,?,?,?)",
                    (client_id, ref, did, now, now))
                tech_crees += 1
            # demandes_compteurs
            cursor.execute("SELECT id FROM demandes_compteurs WHERE reference=?", (ref,))
            if not cursor.fetchone():
                # Détecter type compteur depuis code_compteur
                cursor.execute("SELECT code_compteur FROM clients WHERE id=?", (client_id,))
                row = cursor.fetchone()
                code = str(row[0] or '') if row else ''
                type_ctr = 'MONO' if (code and code[0] in '123') else 'TRI'
                cursor.execute(
                    "INSERT INTO demandes_compteurs (reference,installateur,type_compteur,district_id,date_creation,date_modification) VALUES (?,?,?,?,?,?)",
                    (ref, inst or '', type_ctr, did, now, now))
                ctr_crees += 1
        conn.commit()
    return jsonify({'tech_crees': tech_crees, 'ctr_crees': ctr_crees, 'total': len(clients)})


@app.route('/api/clients_light_full')
@login_required
def api_clients_light_full():
    district = session.get('district')
    clients = db.get_clients_by_district(district)
    return jsonify([{
        'reference': c['reference'],
        'nom': c.get('nom',''),
        'installateurCode': c.get('installateurCode') or c.get('installateur',''),
        'opip': c.get('opip',''),
        'codeCompteur': c.get('codeCompteur',''),
        'dateDepot': c.get('dateDepot',''),
        'dateFraisDossier': c.get('dateFraisDossier',''),
        'puissance_onduleur': c.get('puissance_onduleur',0),
        'puissance_element': c.get('puissance_element',250),
        'nbModules': c.get('nbModules',0),
    } for c in clients])

@app.route('/api/clients_light')
@login_required
def api_clients_light():
    return jsonify(db.get_clients_light_by_district(session.get('district')))

@app.route('/api/sync_technique_compteur', methods=['POST'])
@login_required
def api_sync_technique_compteur():
    data = request.get_json()
    if not data or not data.get('reference'): return jsonify({'error': 'Référence manquante'}), 400
    ok = db.sync_technique_to_compteur(data['reference'], data)
    return jsonify({'status': 'synced' if ok else 'not_found'})

@app.route('/planning_reception')
@login_required
@access_required('planning')
def planning_reception():
    return render_template('planning_reception.html',
        username=session.get('username'),
        district=session.get('district'),
        role=session.get('role'))


# ==================== API PLANNING RÉCEPTION ====================


@app.route('/api/statistiques_pv')
@login_required
def api_statistiques_pv():
    import sqlite3 as _sq, json as _j
    district = session.get('district')
    db2 = Database()
    did = db2.get_district_id_by_nom(district)
    if not did: return jsonify({'error': 'District introuvable'}), 400

    date_ref   = request.args.get('date_ref', '')    # date de référence (stat 1,2,5,6)
    date_debut = request.args.get('date_debut', '')  # période début (stat 4)
    date_fin   = request.args.get('date_fin', '')    # période fin   (stat 4)

    with db2.get_connection() as conn:
        conn.row_factory = _sq.Row
        c = conn.cursor()

        # Stat 1 : demandes en instance (date_demande_reception non vide, date_pose vide)
        # jusqu'à date_ref
        q1 = """SELECT COUNT(*) FROM demandes_compteurs
                WHERE district_id=?
                AND TRIM(COALESCE(date_demande_reception,''))!=''
                AND TRIM(COALESCE(date_pose,''))=''"""
        p1 = [did]
        if date_ref:
            q1 += " AND date_demande_reception<=?"
            p1.append(date_ref)
        c.execute(q1, p1)
        stat1 = c.fetchone()[0]

        # Stat 2 : nouvelles demandes à partir de date_ref
        q2 = """SELECT COUNT(*) FROM demandes_compteurs
                WHERE district_id=?
                AND TRIM(COALESCE(date_demande_reception,''))!=''"""
        p2 = [did]
        if date_ref:
            q2 += " AND date_demande_reception>=?"
            p2.append(date_ref)
        c.execute(q2, p2)
        stat2 = c.fetchone()[0]

        # Stat 3 : demandes satisfaites (date_pose non vide)
        c.execute("""SELECT COUNT(*) FROM demandes_compteurs
                     WHERE district_id=?
                     AND TRIM(COALESCE(date_pose,''))!=''""", (did,))
        stat3 = c.fetchone()[0]

        # Stat 4 : compteurs posés dans la période [date_debut, date_fin]
        q4 = """SELECT COUNT(*) FROM demandes_compteurs
                WHERE district_id=?
                AND TRIM(COALESCE(date_pose,''))!=''"""
        p4 = [did]
        if date_debut:
            q4 += " AND date_pose>=?"; p4.append(date_debut)
        if date_fin:
            q4 += " AND date_pose<=?"; p4.append(date_fin)
        c.execute(q4, p4)
        stat4 = c.fetchone()[0]

        # Stat 5 : délai moyen étude = date_approbation(AC) - date_depot(R) sur clients
        q5 = """SELECT cl.date_approbation, cl.date_depot
                FROM clients cl
                WHERE cl.district_id=?
                AND TRIM(COALESCE(cl.date_approbation,''))!=''
                AND TRIM(COALESCE(cl.date_depot,''))!=''"""
        p5 = [did]
        if date_ref:
            q5 += " AND cl.date_approbation<=?"; p5.append(date_ref)
        c.execute(q5, p5)
        rows5 = c.fetchall()
        delais5 = []
        from datetime import datetime
        for r in rows5:
            try:
                d1 = datetime.strptime(r['date_depot'][:10], '%Y-%m-%d')
                d2 = datetime.strptime(r['date_approbation'][:10], '%Y-%m-%d')
                delais5.append((d2-d1).days)
            except: pass
        stat5 = round(sum(delais5)/len(delais5), 1) if delais5 else None

        # Stat 6 : délai moyen branchement = date_pose(U) - date_demande_reception(S)
        q6 = """SELECT date_pose, date_demande_reception FROM demandes_compteurs
                WHERE district_id=?
                AND TRIM(COALESCE(date_pose,''))!=''
                AND TRIM(COALESCE(date_demande_reception,''))!=''"""
        p6 = [did]
        if date_ref:
            q6 += " AND date_pose<=?"; p6.append(date_ref)
        c.execute(q6, p6)
        rows6 = c.fetchall()
        delais6 = []
        for r in rows6:
            try:
                d1 = datetime.strptime(r['date_demande_reception'][:10], '%Y-%m-%d')
                d2 = datetime.strptime(r['date_pose'][:10], '%Y-%m-%d')
                delais6.append((d2-d1).days)
            except: pass
        stat6 = round(sum(delais6)/len(delais6), 1) if delais6 else None

        # Stat 7 : total dossiers traités (date_pose non vide)
        c.execute("""SELECT COUNT(*) FROM demandes_compteurs
                     WHERE district_id=? AND TRIM(COALESCE(date_pose,''))!=''""", (did,))
        stat7 = c.fetchone()[0]

        # Stat 8 : puissance totale crête (somme puissance_totale des clients avec date_pose non vide)
        c.execute("""SELECT COALESCE(SUM(cl.puissance_totale),0)
                     FROM clients cl
                     JOIN demandes_compteurs dc ON cl.reference=dc.reference
                     WHERE cl.district_id=?
                     AND TRIM(COALESCE(dc.date_pose,''))!=''""", (did,))
        stat8 = c.fetchone()[0] or 0

    return jsonify({
        'stat1': stat1, 'stat2': stat2, 'stat3': stat3, 'stat4': stat4,
        'stat5': stat5, 'stat6': stat6, 'stat7': stat7, 'stat8': stat8,
    })

@app.route('/api/planning_reception_debug/<ref>')
@login_required
def api_planning_reception_debug(ref):
    import sqlite3, json as _j
    district = session.get('district')
    db2 = Database()
    did = db2.get_district_id_by_nom(district)
    with db2.get_connection() as conn:
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("SELECT dt.reference, dt.donnees_techniques, dt.date_reception_technique, dt.avis_technique, cl.opip FROM dossiers_techniques dt LEFT JOIN clients cl ON dt.reference=cl.reference WHERE dt.reference=?", (ref,))
        r = c.fetchone()
        if not r: return jsonify({'error': 'not in dossiers_techniques'})
        tech = {}
        try: tech = _j.loads(r['donnees_techniques'] or '{}')
        except: pass
        c.execute("SELECT date_demande_reception, date_reception_technique, arrivage FROM demandes_compteurs WHERE reference=?", (ref,))
        d = c.fetchone()
        dem = dict(d) if d else {}
    avis_doss = (tech.get('avis_doss') or '').strip()
    avis_ok = 'RAS' in avis_doss.upper() or 'APPROUV' in avis_doss.upper()
    if not avis_ok:
        at = (r['avis_technique'] or '').upper()
        avis_ok = 'RAS' in at or 'APPROUV' in at
    rec_date_demande = (tech.get('rec_date_demande') or dem.get('date_demande_reception') or '').strip()
    rec_date = (tech.get('rec_date') or dem.get('date_reception_technique') or '').strip()
    rec_avis = (tech.get('rec_avis') or '').strip().upper()
    no_serie = (tech.get('ctr_n_serie') or '').strip().upper()
    opip = (r['opip'] or '').strip().upper()
    return jsonify({
        'district_id': did,
        'avis_doss': avis_doss, 'avis_technique': r['avis_technique'], 'avis_ok': avis_ok,
        'rec_date_demande_tech': tech.get('rec_date_demande'),
        'rec_date_demande_ctr': dem.get('date_demande_reception'),
        'rec_date_demande_final': rec_date_demande,
        'rec_date_tech': tech.get('rec_date'),
        'rec_date_ctr': dem.get('date_reception_technique'),
        'rec_date_final': rec_date,
        'rec_avis': rec_avis,
        'no_serie': no_serie, 'opip': opip,
        'condition_ok': bool(avis_ok and rec_date_demande and not rec_date and not rec_avis and no_serie != 'ANNULE' and opip != 'ANNULE'),
        'date_reception_technique_dossier': r['date_reception_technique'],
    })

@app.route('/api/planning_reception')
@login_required
def api_planning_reception():
    import sqlite3, json as _j, traceback as _tb
    try:
        district = session.get('district')
        db2 = Database()
        did = db2.get_district_id_by_nom(district)
        if not did: return jsonify([])

        with db2.get_connection() as conn:
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            c.execute("""
                SELECT dt.reference, dt.donnees_techniques, dt.date_reception_technique,
                       dt.avis_technique,
                       cl.nom, cl.adresse, cl.programme, cl.installateur_code,
                       cl.code_compteur, cl.opip
                FROM dossiers_techniques dt
                LEFT JOIN clients cl ON dt.reference = cl.reference
                WHERE dt.district_id = ?
            """, (did,))
            rows = c.fetchall()
            # Charger arrivage depuis demandes_compteurs
            c.execute("""SELECT reference, arrivage, date_demande_reception, date_reception_technique
                           FROM demandes_compteurs WHERE district_id=?""", (did,))
            demandes_map = {}
            for r2 in c.fetchall():
                demandes_map[r2['reference']] = {
                    'arrivage': r2['arrivage'] or '',
                    'date_demande_reception': r2['date_demande_reception'] or '',
                    'date_reception_technique': r2['date_reception_technique'] or '',
                }
            arrivage_map = {k: v['arrivage'] for k, v in demandes_map.items()}

        result = []
        for r in rows:
            tech = {}
            try: tech = _j.loads(r['donnees_techniques'] or '{}')
            except: pass

            avis_doss = (tech.get('avis_doss') or '').strip()
            avis_doss_upper = avis_doss.upper()
            avis_ok = ('RAS' in avis_doss_upper or 'APPROUV' in avis_doss_upper)
            if not avis_ok:
                try: at = (r['avis_technique'] or '').upper()
                except: at = ''
                avis_ok = ('RAS' in at or 'APPROUV' in at)

            ref_key = r['reference']
            dem = demandes_map.get(ref_key, {})
            # col.S : priorité technique.html, fallback compteurs.html
            rec_date_demande = (tech.get('rec_date_demande') or dem.get('date_demande_reception') or '').strip()
            # col.T : priorité technique.html, fallback compteurs.html
            rec_date = (tech.get('rec_date') or dem.get('date_reception_technique') or '').strip()
            rec_avis = (tech.get('rec_avis') or '').strip().upper()

            # Exclusions : N° série = ANNULE ou OPIP = ANNULE
            no_serie = (tech.get('ctr_n_serie') or '').strip().upper()
            opip = (r['opip'] or '').strip().upper()
            if no_serie == 'ANNULE' or opip == 'ANNULE': continue

            # Date Pose col.U — doit être vide pour figurer dans le planning réception
            date_pose = (tech.get('ctr_n_date') or tech.get('rec_date_pose') or '').strip()

            if (avis_ok and rec_date_demande and not rec_date and not date_pose and not rec_avis):
                codeCompteur = str(r['code_compteur'] or '202').strip()
                firstDigit = int(codeCompteur[0]) if codeCompteur and codeCompteur[0].isdigit() else 2
                typeCompteur = 'MONO' if firstDigit < 4 else 'TRI'
                ref = r['reference']
                # Récupérer le nom installateur depuis la colonne installateur si disponible
                inst_name = ''
                try:
                    c.execute("SELECT COALESCE(installateur,'') FROM clients WHERE reference=?", (ref,))
                    ir = c.fetchone()
                    inst_name = ir[0] if ir else ''
                except: pass
                inst_name = inst_name or r['installateur_code'] or ''
                result.append({
                    'reference': ref,
                    'nom': r['nom'] or '',
                    'installateur': inst_name,
                    'programme': r['programme'] or '',
                    'adresse': r['adresse'] or '',
                    'type_compteur': typeCompteur,
                    'avis_doss': avis_doss or '',
                    'rec_date_demande': rec_date_demande,
                    'avis_agent': tech.get('avis_agent') or '',
                    'date_reception_dossier': r['date_reception_technique'] or '',
                    'arrivage': arrivage_map.get(ref, ''),
                })

        return jsonify(sorted(result, key=lambda x: x['rec_date_demande'] or ''))
    except Exception as e:
        return jsonify({'error': str(e), 'trace': _tb.format_exc()}), 500


@app.route('/api/planning_pose_compteurs')
@login_required
def api_planning_pose_compteurs():
    """Liste 2 : Planning de Pose Compteurs
       Critères :
         - avis labo (col.J) = 'OUI'
         - date_pose vide
         - N° série non vide et != ANNULE
         - OPIP != ANNULE
         - avis_reception = 'RAS' (strict — exclut vide/RÉSERVES)
         - date_reception_technique (col.T) fournie en retour
    """
    import sqlite3, json as _j, traceback as _tb
    try:
        district = session.get('district')
        db2 = Database()
        did = db2.get_district_id_by_nom(district)
        if not did: return jsonify([])

        with db2.get_connection() as conn:
            conn.row_factory = sqlite3.Row
            c = conn.cursor()

            # ── Table principale : demandes_compteurs avec avis labo = OUI et pas posé ──
            c.execute("""
                SELECT dc.reference, dc.installateur, dc.date_pose, dc.avis,
                       dc.avis_reception, dc.no_serie, dc.type_compteur, dc.arrivage,
                       dc.date_demande_reception, dc.date_approbation,
                       dc.date_reception_arrivage,
                       cl.nom, cl.programme, cl.code_compteur, cl.installateur_code, cl.opip
                FROM demandes_compteurs dc
                LEFT JOIN clients cl ON dc.reference = cl.reference
                WHERE dc.district_id = ?
                  AND UPPER(TRIM(COALESCE(dc.avis,''))) = 'OUI'
                  AND (dc.date_pose IS NULL OR TRIM(dc.date_pose) = '')
            """, (did,))
            dc_rows = c.fetchall()

            # ── Charger donnees_techniques pour rec_avis + opip + no_serie ──
            c.execute("""
                SELECT reference, donnees_techniques
                FROM dossiers_techniques WHERE district_id = ?
            """, (did,))
            dt_map = {}
            for row in c.fetchall():
                try: dt_map[row['reference']] = _j.loads(row['donnees_techniques'] or '{}')
                except: dt_map[row['reference']] = {}

        result = []
        for r in dc_rows:
            ref = r['reference']
            tech = dt_map.get(ref, {})

            # Exclusion 1 : N° série != ANNULE (peut être vide)  |  OPIP != ANNULE
            no_serie_dc   = (r['no_serie'] or '').strip().upper()
            no_serie_tech = (tech.get('ctr_n_serie') or '').strip().upper()
            no_serie_val  = no_serie_dc or no_serie_tech
            opip = (r['opip'] or '').strip().upper()
            # Exclure seulement si ANNULE (le N° série peut être vide)
            if no_serie_val == 'ANNULE': continue
            if opip == 'ANNULE': continue

            # Exclusion 2 : date_pose déjà renseignée dans dossiers_techniques
            # ctr_n_date = Date Pose col.U (onglet Réception Technique)
            rec_date_pose_dt = (tech.get('ctr_n_date') or tech.get('rec_date_pose') or '').strip()
            if rec_date_pose_dt: continue

            # Critère strict : Avis Réception = RAS uniquement
            avis_rec_dc = (r['avis_reception'] or '').strip().upper()
            avis_rec_dt = (tech.get('rec_avis') or '').strip().upper()
            avis_rec = avis_rec_dc or avis_rec_dt
            if avis_rec != 'RAS': continue   # exclure vide, RÉSERVES, ANNULE, etc.

            # Date Réception Technique (col.T) depuis dossiers_techniques.donnees_techniques
            date_rec_technique = (tech.get('rec_date') or '').strip()

            # Type compteur
            type_ctr = r['type_compteur'] or ''
            if not type_ctr:
                code = str(r['code_compteur'] or '202').strip()
                fd = int(code[0]) if code and code[0].isdigit() else 2
                type_ctr = 'MONO' if fd < 4 else 'TRI'

            no_serie = no_serie_dc or no_serie_tech
            installateur = r['installateur_code'] or r['installateur'] or ''

            result.append({
                'reference': ref,
                'nom': r['nom'] or '',
                'installateur': installateur,
                'programme': r['programme'] or '',
                'type_compteur': type_ctr,
                'no_serie': no_serie,
                'arrivage': r['arrivage'] or '',
                'avis_reception': avis_rec,
                'avis_labo': (r['avis'] or '').upper(),
                'date_reception_technique': date_rec_technique,
            })

        return jsonify(sorted(result, key=lambda x: x['no_serie'] or ''))
    except Exception as e:
        return jsonify({'error': str(e), 'trace': _tb.format_exc()}), 500


@app.route('/api/session_info')
@login_required
def api_session_info():
    return jsonify({
        'username': session.get('username'),
        'nom_complet': session.get('nom_complet'),
        'district': session.get('district'),
        'role': session.get('role')
    })


# ==================== CDN LOCAL CACHE ====================
# Télécharge automatiquement les libs CDN au premier accès
_CDN_MAP = {
    '/static/css/bootstrap.min.css':       'https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css',
    '/static/js/bootstrap.bundle.min.js':  'https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js',
    '/static/fa/css/all.min.css':          'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css',
    '/static/js/xlsx.full.min.js':         'https://cdnjs.cloudflare.com/ajax/libs/xlsx/0.18.5/xlsx.full.min.js',
    '/static/js/qrcode.min.js':            'https://cdnjs.cloudflare.com/ajax/libs/qrcodejs/1.0.0/qrcode.min.js',
    '/static/js/chart.min.js':             'https://cdn.jsdelivr.net/npm/chart.js@3.9.1/dist/chart.min.js',
}
_FA_WEBFONTS = [
    'fa-solid-900.woff2','fa-solid-900.woff','fa-solid-900.ttf',
    'fa-regular-400.woff2','fa-regular-400.woff','fa-brands-400.woff2',
    'fa-brands-400.ttf',
]
for _wf in _FA_WEBFONTS:
    _CDN_MAP[f'/static/fa/webfonts/{_wf}'] = f'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/webfonts/{_wf}'

def _ensure_static(local_path):
    """Télécharger le fichier CDN si absent en local."""
    full = os.path.join(os.path.dirname(os.path.abspath(__file__)), local_path.lstrip('/'))
    if os.path.exists(full) and os.path.getsize(full) > 100:
        return True
    url = _CDN_MAP.get(local_path)
    if not url:
        return False
    try:
        import urllib.request
        os.makedirs(os.path.dirname(full), exist_ok=True)
        urllib.request.urlretrieve(url, full)
        return os.path.getsize(full) > 100
    except Exception as e:
        print(f"[CDN] Impossible de télécharger {url}: {e}")
        return False

@app.before_request
def auto_download_cdn():
    """Télécharger les libs CDN manquantes au premier accès."""
    if request.path.startswith('/static/'):
        full = os.path.join(os.path.dirname(os.path.abspath(__file__)), request.path.lstrip('/'))
        if not os.path.exists(full) or os.path.getsize(full) < 100:
            _ensure_static(request.path)

# Télécharger toutes les libs au démarrage (en tâche de fond)
def _download_all_cdn():
    import time as _t
    _t.sleep(3)  # Laisser Flask démarrer d'abord
    for local_path in list(_CDN_MAP.keys()):
        _ensure_static(local_path)

import threading as _th
_th.Thread(target=_download_all_cdn, daemon=True).start()

# ==================== RUN ====================

# ==================== CONFIGURATION EMAIL ====================
# Fichier de config email : data/email_config.json
import json as _json

def _get_email_config():
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'email_config.json')
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return _json.load(f)
        except Exception:
            pass
    return {}

def _save_email_config(cfg):
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
    os.makedirs(data_dir, exist_ok=True)  # Créer le dossier data/ si absent
    path = os.path.join(data_dir, 'email_config.json')
    with open(path, 'w', encoding='utf-8') as f:
        _json.dump(cfg, f, indent=2, ensure_ascii=False)

@app.route('/api/email_config', methods=['GET'])
@login_required
def api_get_email_config():
    try:
        cfg = _get_email_config()
        safe = {k: v for k, v in cfg.items() if k != 'password'}
        safe['has_password'] = bool(cfg.get('password'))
        return jsonify(safe)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/email_config', methods=['POST'])
@login_required
def api_save_email_config():
    try:
        d = request.get_json() or {}
        cfg = _get_email_config()
        cfg['smtp_host']  = d.get('smtp_host', cfg.get('smtp_host', ''))
        cfg['smtp_port']  = int(d.get('smtp_port', cfg.get('smtp_port', 587)))
        cfg['smtp_user']  = d.get('smtp_user', cfg.get('smtp_user', ''))
        cfg['from_email'] = d.get('from_email', cfg.get('from_email', ''))
        cfg['from_name']  = d.get('from_name', cfg.get('from_name', 'STEG PV'))
        cfg['use_tls']    = bool(d.get('use_tls', cfg.get('use_tls', True)))
        if d.get('password'):
            cfg['password'] = d['password']
        _save_email_config(cfg)
        return jsonify({'status': 'saved'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/envoyer_avis', methods=['POST'])
@login_required
def api_envoyer_avis():
    """Envoyer l'avis technique par email à l'installateur"""
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart

    d = request.get_json() or {}
    dest_email    = (d.get('dest_email') or '').strip()
    dest_nom      = (d.get('dest_nom') or 'Installateur').strip()
    reference     = (d.get('reference') or '').strip()
    nom_client    = (d.get('nom_client') or '').strip()
    avis          = (d.get('avis') or '').strip()
    reserves      = (d.get('reserves') or '').strip()
    agent         = (d.get('agent') or '').strip()
    date_avis     = (d.get('date_avis') or '').strip()

    if not dest_email:
        return jsonify({'error': 'Email destinataire manquant'}), 400

    cfg = _get_email_config()
    if not cfg.get('smtp_host') or not cfg.get('smtp_user') or not cfg.get('password'):
        return jsonify({'error': 'Configuration email non renseignée — allez dans Admin Global → Système → Config Email'}), 400

    # Construire l'email HTML
    couleur = '#28a745' if avis == 'RAS' else '#dc3545'
    reserves_html = ('<p><b>Réserves :</b></p><ul>' + ''.join(f'<li>{r.strip()}</li>' for r in reserves.split('\n') if r.strip()) + '</ul>') if reserves else ''

    html_body = f"""
    <div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;border:2px solid #003366;border-radius:8px;">
      <div style="background:#003366;color:#FFCC00;padding:16px 20px;border-radius:6px 6px 0 0;">
        <h2 style="margin:0;">STEG – Avis Dossier Technique PV</h2>
      </div>
      <div style="padding:20px;">
        <p>Bonjour <b>{dest_nom}</b>,</p>
        <p>Nous vous informons de la décision technique concernant le dossier :</p>
        <table style="width:100%;border-collapse:collapse;margin:12px 0;">
          <tr><td style="padding:6px 10px;background:#f0f4ff;font-weight:bold;border:1px solid #ddd;">Référence</td><td style="padding:6px 10px;border:1px solid #ddd;">{reference}</td></tr>
          <tr><td style="padding:6px 10px;background:#f0f4ff;font-weight:bold;border:1px solid #ddd;">Client</td><td style="padding:6px 10px;border:1px solid #ddd;">{nom_client}</td></tr>
          <tr><td style="padding:6px 10px;background:#f0f4ff;font-weight:bold;border:1px solid #ddd;">Avis Technique</td><td style="padding:6px 10px;border:1px solid #ddd;"><b style="color:{couleur};font-size:16px;">{avis}</b></td></tr>
          <tr><td style="padding:6px 10px;background:#f0f4ff;font-weight:bold;border:1px solid #ddd;">Date</td><td style="padding:6px 10px;border:1px solid #ddd;">{date_avis}</td></tr>
          <tr><td style="padding:6px 10px;background:#f0f4ff;font-weight:bold;border:1px solid #ddd;">Agent vérificateur</td><td style="padding:6px 10px;border:1px solid #ddd;">{agent}</td></tr>
        </table>
        {reserves_html}
        <p style="color:#555;font-size:12px;border-top:1px solid #eee;padding-top:10px;margin-top:16px;">
          Cet email a été envoyé automatiquement par le système STEG PV.
        </p>
      </div>
    </div>
    """

    msg = MIMEMultipart('alternative')
    msg['Subject'] = f"Avis Technique PV — {reference} — {avis}"
    msg['From']    = f"{cfg.get('from_name','STEG PV')} <{cfg.get('from_email', cfg['smtp_user'])}>"
    msg['To']      = dest_email
    msg.attach(MIMEText(html_body, 'html', 'utf-8'))

    try:
        import ssl
        smtp_host = cfg['smtp_host']
        smtp_port = int(cfg.get('smtp_port', 587))
        use_tls   = cfg.get('use_tls', True)

        # Auto-détection Yahoo Mail → SSL port 465
        is_yahoo = 'yahoo' in smtp_host.lower()
        if is_yahoo:
            smtp_port = 465
            use_tls   = False  # Yahoo = SSL direct, pas STARTTLS

        if use_tls:
            # STARTTLS (Gmail, Outlook, etc.)
            server = smtplib.SMTP(smtp_host, smtp_port, timeout=20)
            server.ehlo()
            server.starttls()
            server.ehlo()
        else:
            # SSL direct (Yahoo, port 465)
            ctx = ssl.create_default_context()
            server = smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=20, context=ctx)
            server.ehlo()

        server.login(cfg['smtp_user'], cfg['password'])
        server.sendmail(msg['From'], [dest_email], msg.as_string())
        server.quit()
        return jsonify({'status': 'sent', 'message': f'Email envoyé à {dest_email}'})
    except smtplib.SMTPAuthenticationError:
        return jsonify({'error': 'Erreur authentification — vérifiez le mot de passe SMTP. Pour Yahoo : utilisez un "App Password" (mot de passe application).'}), 500
    except smtplib.SMTPConnectError as e:
        return jsonify({'error': f'Impossible de se connecter au serveur SMTP ({smtp_host}:{smtp_port}): {e}'}), 500
    except Exception as e:
        return jsonify({'error': f'Erreur SMTP: {str(e)}'}), 500

# ==================== ACCÈS RÉSEAU ====================
import socket as _socket

def _get_all_ips():
    """Retourne toutes les IPs locales disponibles"""
    ips = []
    try:
        hostname = _socket.gethostname()
        infos = _socket.getaddrinfo(hostname, None)
        for info in infos:
            ip = info[4][0]
            if ip.startswith('192.168.') or ip.startswith('10.') or ip.startswith('172.'):
                if ip not in ips:
                    ips.append(ip)
    except: pass
    try:
        s = _socket.socket(_socket.AF_INET, _socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        if ip not in ips: ips.append(ip)
    except: pass
    return ips or ['127.0.0.1']

@app.route('/api/network_info')
@login_required
def api_network_info():
    """Retourne les IPs disponibles pour accès réseau"""
    ips = _get_all_ips()
    port = int(os.environ.get('STEG_PORT', 5000))
    return jsonify({
        'ips': ips,
        'port': port,
        'urls': [f'http://{ip}:{port}' for ip in ips],
        'local': f'http://127.0.0.1:{port}'
    })

@app.route('/api/open_firewall', methods=['POST'])
@login_required
def api_open_firewall():
    """Ouvre le port dans le pare-feu Windows (admin requis)"""
    auths = session.get('autorisations', [])
    if 'admin' not in auths and 'superadmin' not in auths:
        return jsonify({'error': 'Admin requis'}), 403
    port = int(os.environ.get('STEG_PORT', 5000))
    import subprocess as _sp
    # Supprimer règle existante puis recréer
    _sp.run(['netsh','advfirewall','firewall','delete','rule','name=STEG_PV_HTTP'],
            capture_output=True, shell=True)
    r = _sp.run(
        ['netsh','advfirewall','firewall','add','rule',
         'name=STEG_PV_HTTP','dir=in','action=allow',
         'protocol=TCP',f'localport={port}','profile=any'],
        capture_output=True, text=True, shell=True)
    if r.returncode == 0:
        ips = _get_all_ips()
        return jsonify({'success': True, 'message': f'Port {port} ouvert.',
                        'urls': [f'http://{ip}:{port}' for ip in ips], 'ips': ips, 'port': port})
    else:
        # Accès refusé → retourner instruction pour script avec élévation UAC
        return jsonify({
            'error': 'Droits insuffisants',
            'need_uac': True,
            'message': 'Lancez le script OUVRIR_PAREFEU.bat depuis le dossier STEG PV (double-clic, accepter l\'élévation).'
        }), 403

@app.route('/download/parefeu')
@login_required
def download_parefeu():
    """Télécharger le script d'ouverture du pare-feu avec élévation UAC"""
    port = int(os.environ.get('STEG_PORT', 5000))
    content = f"""@echo off
chcp 1252 >nul 2>&1
title STEG PV - Pare-feu
net session >nul 2>&1
IF %ERRORLEVEL% EQU 0 goto :has_admin
powershell -NoProfile -Command "Start-Process '%~f0' -Verb RunAs"
exit /b
:has_admin
echo.
echo STEG PV - Ouverture du port {port} dans le pare-feu
echo.
netsh advfirewall firewall delete rule name="STEG_PV_HTTP" >nul 2>&1
netsh advfirewall firewall add rule name="STEG_PV_HTTP" dir=in action=allow protocol=TCP localport={port} profile=any
IF %ERRORLEVEL% EQU 0 (echo [OK] Port {port} ouvert - Acces Android/reseau actif) ELSE (echo [ERREUR] Echec)
echo.
pause
"""
    from flask import Response
    return Response(
        content,
        mimetype='application/octet-stream',
        headers={'Content-Disposition': 'attachment; filename=OUVRIR_PAREFEU.bat'}
    )

@app.route('/reseau')
@login_required
def page_reseau():
    """Page admin - gestion accès réseau"""
    auths = session.get('autorisations', [])
    is_admin = 'admin' in auths or 'superadmin' in auths
    return render_template('reseau.html',
        username=session.get('username'),
        district=session.get('district'),
        is_admin=is_admin,
        IS_ADMIN=is_admin)


