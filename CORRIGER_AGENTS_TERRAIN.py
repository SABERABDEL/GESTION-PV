#!/usr/bin/env python3
"""
Script de correction automatique - Supprimer l'onglet "Agents Terrain"
et ajouter les droits par onglet bibliothèque dans le modal utilisateur.

UTILISATION:
  1. Copier ce fichier dans votre dossier steg_pack/
  2. Exécuter: python CORRIGER_AGENTS_TERRAIN.py
  3. Redémarrer l'application
"""

import os, re, shutil

TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")

def corriger_fichier(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    original = content
    fichier = os.path.basename(filepath)
    modifications = []

    # ─── 1. Supprimer le bouton onglet "Agents Terrain" ───
    # Pattern flexible pour capturer toute variante du bouton
    pattern_btn = r'<button[^>]*class="[^"]*(?:tab-btn|bib-tb)[^"]*"[^>]*>[^<]*(?:Agents?\s*Terrain|agents_terrain)[^<]*</button>'
    if re.search(pattern_btn, content, re.IGNORECASE):
        content = re.sub(pattern_btn, '', content, flags=re.IGNORECASE)
        modifications.append("✅ Bouton onglet 'Agents Terrain' supprimé")

    # ─── 2. Supprimer le pane/section agents_terrain ───
    # Pour les panes de type <div id="bib_agents_terrain">...</div>
    pattern_pane = r'<!--\s*[=\-]*\s*AGENTS?\s*TERRAIN[^>]*-->\s*<div[^>]*id=["\']bib_agents_terrain["\'][^>]*>.*?</div>\s*'
    if re.search(pattern_pane, content, re.IGNORECASE | re.DOTALL):
        content = re.sub(pattern_pane, '', content, flags=re.IGNORECASE | re.DOTALL)
        modifications.append("✅ Pane 'bib_agents_terrain' supprimé")

    # ─── 3. Supprimer agents_terrain du JS BIB object ───
    content = re.sub(r',\s*agents_terrain\s*:\s*\[\]', '', content)
    content = re.sub(r'agents_terrain\s*:\s*\[\]\s*,?\s*', '', content)
    modifications.append("✅ Nettoyage JS agents_terrain")

    # ─── 4. Supprimer agents_terrain des maps JS ───
    content = re.sub(r',?\s*agents_terrain\s*:\s*[`\'"]?[^,}\n]+[`\'"]?', '', content)
    modifications.append("✅ Nettoyage maps JS agents_terrain")

    # ─── 5. Supprimer les formulaires agents_terrain ───
    pattern_form = r',?\s*agents_terrain\s*:\s*`[^`]*`'
    if re.search(pattern_form, content, re.DOTALL):
        content = re.sub(pattern_form, '', content, flags=re.DOTALL)
        modifications.append("✅ Formulaire agents_terrain supprimé")

    # ─── 6. Ajouter droits bib dans modal utilisateur ───
    # Chercher la section autorisations dans le modal et ajouter après
    BIB_DROITS_HTML = """
    <!-- DROITS ONGLETS BIBLIOTHEQUE - AJOUTÉ AUTOMATIQUEMENT -->
    <div id="bib_droits_section" style="background:#fff8e1;border:1.5px solid #ffe082;border-radius:8px;padding:12px 16px;margin-bottom:16px;display:none;">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
        <label style="font-weight:bold;font-size:13px;color:#b8860b;"><i class="fas fa-book me-1"></i>Droits d'accès aux onglets — Bibliothèques</label>
        <div style="display:flex;gap:6px;">
          <button type="button" onclick="bibDroitsAll(true)"  style="font-size:10px;padding:2px 8px;background:#003366;color:#fff;border:none;border-radius:4px;cursor:pointer;">Tout cocher</button>
          <button type="button" onclick="bibDroitsAll(false)" style="font-size:10px;padding:2px 8px;background:#888;color:#fff;border:none;border-radius:4px;cursor:pointer;">Tout décocher</button>
        </div>
      </div>
      <div style="display:grid;grid-template-columns:repeat(5,1fr);gap:6px;">
        <div style="border:1px solid #ffe082;border-radius:6px;padding:6px 8px;background:#fffde7;">
          <div style="font-weight:bold;font-size:11px;color:#b8860b;margin-bottom:5px;">🔌 Onduleurs</div>
          <label style="display:flex;align-items:center;gap:4px;font-size:11px;margin-bottom:3px;"><input type="checkbox" id="bd_ond_voir"><span>👁 Voir</span></label>
          <label style="display:flex;align-items:center;gap:4px;font-size:11px;margin-bottom:3px;"><input type="checkbox" id="bd_ond_ajouter"><span>➕ Ajouter</span></label>
          <label style="display:flex;align-items:center;gap:4px;font-size:11px;margin-bottom:3px;"><input type="checkbox" id="bd_ond_modifier"><span>✏️ Modifier</span></label>
          <label style="display:flex;align-items:center;gap:4px;font-size:11px;"><input type="checkbox" id="bd_ond_supprimer"><span>🗑️ Supprimer</span></label>
        </div>
        <div style="border:1px solid #ffe082;border-radius:6px;padding:6px 8px;background:#fffde7;">
          <div style="font-weight:bold;font-size:11px;color:#b8860b;margin-bottom:5px;">☀️ Panneaux</div>
          <label style="display:flex;align-items:center;gap:4px;font-size:11px;margin-bottom:3px;"><input type="checkbox" id="bd_pan_voir"><span>👁 Voir</span></label>
          <label style="display:flex;align-items:center;gap:4px;font-size:11px;margin-bottom:3px;"><input type="checkbox" id="bd_pan_ajouter"><span>➕ Ajouter</span></label>
          <label style="display:flex;align-items:center;gap:4px;font-size:11px;margin-bottom:3px;"><input type="checkbox" id="bd_pan_modifier"><span>✏️ Modifier</span></label>
          <label style="display:flex;align-items:center;gap:4px;font-size:11px;"><input type="checkbox" id="bd_pan_supprimer"><span>🗑️ Supprimer</span></label>
        </div>
        <div style="border:1px solid #ffe082;border-radius:6px;padding:6px 8px;background:#fffde7;">
          <div style="font-weight:bold;font-size:11px;color:#b8860b;margin-bottom:5px;">🔗 Câbles DC/AC</div>
          <label style="display:flex;align-items:center;gap:4px;font-size:11px;margin-bottom:3px;"><input type="checkbox" id="bd_cable_voir"><span>👁 Voir</span></label>
          <label style="display:flex;align-items:center;gap:4px;font-size:11px;margin-bottom:3px;"><input type="checkbox" id="bd_cable_ajouter"><span>➕ Ajouter</span></label>
          <label style="display:flex;align-items:center;gap:4px;font-size:11px;margin-bottom:3px;"><input type="checkbox" id="bd_cable_modifier"><span>✏️ Modifier</span></label>
          <label style="display:flex;align-items:center;gap:4px;font-size:11px;"><input type="checkbox" id="bd_cable_supprimer"><span>🗑️ Supprimer</span></label>
        </div>
        <div style="border:1px solid #ffe082;border-radius:6px;padding:6px 8px;background:#fffde7;">
          <div style="font-weight:bold;font-size:11px;color:#b8860b;margin-bottom:5px;">⚡ Codes CTR</div>
          <label style="display:flex;align-items:center;gap:4px;font-size:11px;margin-bottom:3px;"><input type="checkbox" id="bd_ctr_voir"><span>👁 Voir</span></label>
          <label style="display:flex;align-items:center;gap:4px;font-size:11px;margin-bottom:3px;"><input type="checkbox" id="bd_ctr_ajouter"><span>➕ Ajouter</span></label>
          <label style="display:flex;align-items:center;gap:4px;font-size:11px;margin-bottom:3px;"><input type="checkbox" id="bd_ctr_modifier"><span>✏️ Modifier</span></label>
          <label style="display:flex;align-items:center;gap:4px;font-size:11px;"><input type="checkbox" id="bd_ctr_supprimer"><span>🗑️ Supprimer</span></label>
        </div>
        <div style="border:1px solid #ffe082;border-radius:6px;padding:6px 8px;background:#fffde7;">
          <div style="font-weight:bold;font-size:11px;color:#b8860b;margin-bottom:5px;">🏢 Installateurs</div>
          <label style="display:flex;align-items:center;gap:4px;font-size:11px;margin-bottom:3px;"><input type="checkbox" id="bd_inst_voir"><span>👁 Voir</span></label>
          <label style="display:flex;align-items:center;gap:4px;font-size:11px;margin-bottom:3px;"><input type="checkbox" id="bd_inst_ajouter"><span>➕ Ajouter</span></label>
          <label style="display:flex;align-items:center;gap:4px;font-size:11px;margin-bottom:3px;"><input type="checkbox" id="bd_inst_modifier"><span>✏️ Modifier</span></label>
          <label style="display:flex;align-items:center;gap:4px;font-size:11px;"><input type="checkbox" id="bd_inst_supprimer"><span>🗑️ Supprimer</span></label>
        </div>
      </div>
      <div style="margin-top:6px;font-size:10px;color:#888;"><i class="fas fa-info-circle me-1"></i>Ces droits s'appliquent dans la page Bibliothèques. L'Admin a tous les accès.</div>
    </div>"""

    BIB_DROITS_JS = """
// ─── DROITS BIBLIOTHÈQUE PAR ONGLET ─── AJOUTÉ AUTOMATIQUEMENT
const ALL_BIB_TABS_U = ['ond','pan','cable','ctr','inst'];
const ALL_BIB_ACTIONS_U = ['voir','ajouter','modifier','supprimer'];
const ALL_BIB_RIGHTS_U = ALL_BIB_TABS_U.flatMap(t=>ALL_BIB_ACTIONS_U.map(a=>`${t}_${a}`));
function toggleBibDroits(){
  const has = document.getElementById('ua_bibliotheque')?.checked || document.getElementById('au_bibliotheque')?.checked;
  const sec = document.getElementById('bib_droits_section');
  if(sec) sec.style.display = has ? 'block' : 'none';
}
function bibDroitsAll(v){ ALL_BIB_RIGHTS_U.forEach(r=>{ const el=document.getElementById('bd_'+r); if(el) el.checked=v; }); }
"""

    # Injecter JS avant </script> du bloc principal si pas déjà présent
    if 'bibDroitsAll' not in content:
        # Chercher la fonction fermerUserModal ou fermerModal pour injecter avant
        insert_before = 'function fermerUserModal'
        if insert_before not in content:
            insert_before = 'function fermerModal'
        if insert_before in content:
            content = content.replace(insert_before, BIB_DROITS_JS + '\n' + insert_before, 1)
            modifications.append("✅ Fonctions JS droits bibliothèque ajoutées")

    # Injecter HTML du bloc droits bib avant le bouton Enregistrer du modal
    if 'bib_droits_section' not in content:
        # Chercher le bouton Enregistrer dans le modal utilisateur
        patterns_enreg = [
            '<button class="btn-g" onclick="sauvegarderUser()',
            '<button class="btn-g" onclick="saveAgent()',
            'onclick="sauvegarderUser()',
        ]
        for pat in patterns_enreg:
            if pat in content:
                content = content.replace(pat, BIB_DROITS_HTML + '\n    ' + pat, 1)
                modifications.append("✅ Section HTML droits bibliothèque injectée dans modal")
                break

    # ─── 7. Ajouter onchange=toggleBibDroits sur la checkbox bibliothèque ───
    for cb_id in ['ua_bibliotheque', 'au_bibliotheque']:
        old = f'id="{cb_id}"'
        new = f'id="{cb_id}" onchange="toggleBibDroits()"'
        if old in content and 'onchange="toggleBibDroits()"' not in content:
            content = content.replace(old, new, 1)
            modifications.append(f"✅ onchange toggleBibDroits ajouté sur #{cb_id}")

    if content != original:
        # Sauvegarder backup
        shutil.copy2(filepath, filepath + '.bak')
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"\n📄 {fichier} — {len(modifications)} modification(s) :")
        for m in modifications:
            print(f"   {m}")
        print(f"   💾 Backup sauvegardé: {fichier}.bak")
    else:
        print(f"\n📄 {fichier} — Aucune modification nécessaire (déjà à jour)")

def main():
    print("=" * 60)
    print("  CORRECTION AUTOMATIQUE — Agents Terrain + Droits Bib")
    print("=" * 60)

    html_files = [
        os.path.join(TEMPLATES_DIR, f)
        for f in os.listdir(TEMPLATES_DIR)
        if f.endswith('.html') and not f.endswith('.bak')
    ]

    for filepath in sorted(html_files):
        corriger_fichier(filepath)

    print("\n" + "=" * 60)
    print("  ✅ TERMINÉ — Redémarrez l'application")
    print("=" * 60)

if __name__ == "__main__":
    main()
