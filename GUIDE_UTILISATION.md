# Guide d'Utilisation - Système de Gestion Photovoltaïque STEG

Ce guide détaille le fonctionnement et l'administration du système de gestion photovoltaïque.

## 1. Installation et Lancement

### Prérequis
- Python 3.8 ou supérieur.
- Les dépendances listées dans `requirements.txt`.

### Installation
1. Extrayez l'archive.
2. Ouvrez un terminal dans le dossier du projet.
3. Installez les dépendances :
   ```bash
   pip install -r requirements.txt
   ```

### Lancement
- **Sous Windows** : Double-cliquez sur `LANCER_STEG.bat`.
- **Via Terminal** : 
  ```bash
  python main.py
  ```
L'application sera accessible à l'adresse : `http://127.0.0.1:5000`

---

## 2. Administration Globale (Super Admin)

L'interface d'administration globale permet de gérer la structure hiérarchique de la STEG.

### Gestion des Régions et Districts
1. **Sélection d'une Région** : Cliquez sur une région dans la colonne de gauche. Les districts associés s'afficheront au centre.
2. **Ajout d'un District** : Une fois la région sélectionnée, le bouton **+ Ajouter** apparaît dans la colonne des Districts.
3. **Gestion des Agents** : Cliquez sur un district pour voir et gérer les utilisateurs qui y sont rattachés.

### Gestion des Utilisateurs
- Vous pouvez créer des utilisateurs avec différents rôles (TECHNIQUE, COMMERCIAL, RÉCEPTION, etc.).
- **Sécurité** : Les mots de passe sont désormais hachés de manière sécurisée. Lors de la création ou modification, utilisez des mots de passe robustes.
- **Autorisations** : Cochez les cases correspondantes pour donner accès aux différents modules (Bibliothèque, Statistiques, Import, etc.).

---

## 3. Modules de Gestion

### Module Technique
Permet le suivi des dossiers techniques, la gestion des visites et des rapports.

### Module Commercial
Dédié à la gestion des clients, des contrats et du suivi administratif.

### Bibliothèque
Répertoire centralisé des documents et références techniques.

---

## 4. Maintenance et Sécurité

### Sauvegarde
Les données sont stockées dans le dossier `data/` (fichier `photovoltaique.db`). Il est recommandé de copier ce dossier régulièrement pour sauvegarde.

### Mise à jour de la sécurité
Le système a été mis à jour pour utiliser le hachage `scrypt`. Si un ancien utilisateur ne parvient pas à se connecter, un administrateur peut réinitialiser son mot de passe pour forcer la mise à jour vers le nouveau format sécurisé.

---
*Document généré par Manus AI - Mars 2026*
