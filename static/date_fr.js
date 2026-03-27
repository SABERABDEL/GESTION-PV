/**
 * date_fr.js — Affichage des dates en format français dd/mm/yyyy
 * Les input[type=date] sont remplacés par un input[type=text] visible
 * + un input[type=hidden] qui garde la valeur yyyy-mm-dd pour la DB.
 */
(function() {

    function toFR(iso) {
        if (!iso) return '';
        const m = iso.match(/^(\d{4})-(\d{2})-(\d{2})/);
        if (m) return m[3] + '/' + m[2] + '/' + m[1];
        return iso;
    }

    function toISO(fr) {
        if (!fr) return '';
        if (/^\d{4}-\d{2}-\d{2}/.test(fr)) return fr.substring(0, 10);
        const m = fr.match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})$/);
        if (m) return m[3] + '-' + m[2].padStart(2,'0') + '-' + m[1].padStart(2,'0');
        // Saisie partielle — retourner vide
        return '';
    }

    function applyMask(txt, hidId) {
        txt.addEventListener('input', function() {
            const raw = this.value.replace(/\D/g, '').substring(0, 8);
            let result = '';
            if (raw.length > 0) result = raw.substring(0, Math.min(2, raw.length));
            if (raw.length > 2) result += '/' + raw.substring(2, Math.min(4, raw.length));
            if (raw.length > 4) result += '/' + raw.substring(4, 8);
            this.value = result;
            const hid = document.getElementById(hidId);
            if (hid) hid.value = (raw.length === 8) ? toISO(result) : '';
        });
        txt.addEventListener('blur', function() {
            const hid = document.getElementById(hidId);
            if (!hid) return;
            if (!this.value.trim()) { hid.value = ''; return; }
            const iso = toISO(this.value);
            if (iso) { hid.value = iso; this.value = toFR(iso); }
            else { this.value = toFR(hid.value); } // annuler saisie invalide
        });
    }

    function initDateFields() {
        document.querySelectorAll('input[type="date"]:not([data-fr-init])').forEach(function(el) {
            if (el.dataset.frInit) return;
            el.dataset.frInit = '1';
            const id = el.id;
            const val = el.value || '';

            // Champ texte visible
            const txt = document.createElement('input');
            txt.type = 'text';
            txt.className = el.className;
            txt.placeholder = 'jj/mm/aaaa';
            txt.maxLength = 10;
            txt.autocomplete = 'off';
            txt.style.cssText = el.style.cssText;
            txt.dataset.frInit = '1';
            if (val) txt.value = toFR(val);

            // Champ hidden (prend le vrai id)
            const hid = document.createElement('input');
            hid.type = 'hidden';
            hid.id = id;
            hid.value = val;

            // Cacher l'original, changer son id
            el.id = id ? id + '__orig' : '';
            el.style.display = 'none';

            el.parentNode.insertBefore(txt, el.nextSibling);
            el.parentNode.insertBefore(hid, txt.nextSibling);

            if (id) {
                applyMask(txt, id);
                // Stocker la référence txt dans un attribut pour setDateFR
                txt.id = id + '__txt';
            }
        });
    }

    // setDateFR(id, 'yyyy-mm-dd') → met à jour hidden + affichage txt
    window.setDateFR = function(id, val) {
        const hid = document.getElementById(id);
        if (!hid) {
            // Peut-être pas encore initialisé — fallback direct
            const el = document.getElementById(id + '__orig');
            if (el) el.value = val || '';
            return;
        }
        hid.value = val || '';
        const txt = document.getElementById(id + '__txt');
        if (txt) txt.value = val ? toFR(val) : '';
    };

    window.toISODate = toISO;
    window.toFRDate  = toFR;
    window.reinitDateFields = initDateFields;

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function() {
            initDateFields();
            // Ré-appliquer après 300ms pour les champs créés dynamiquement
            setTimeout(initDateFields, 300);
        });
    } else {
        initDateFields();
        setTimeout(initDateFields, 300);
    }

})();
