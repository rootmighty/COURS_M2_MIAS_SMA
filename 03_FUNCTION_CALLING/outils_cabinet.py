"""
outils_cabinet.py
-----------------
Les "outils" de Doc'Assist : de simples fonctions Python qui lisent et
modifient l'agenda du cabinet (fichier agenda.json).

Aucune IA ici ! Ce sont des fonctions classiques, comme on en écrit tous les jours.
Tout l'enjeu de l'étape est de permettre au LLM de DEMANDER leur exécution.

Tester les outils seuls :
    python 03_FUNCTION_CALLING/outils_cabinet.py

Remettre l'agenda à zéro (par exemple après les tests de réservation) :
    python 03_FUNCTION_CALLING/outils_cabinet.py --reset
"""

import json
import random
import sys
from datetime import date, timedelta
from pathlib import Path

# --- Configuration ---------------------------------------------------------
# L'agenda est stocké dans un fichier JSON placé à côté de ce script.
# Path(__file__).parent = dossier de ce fichier, quel que soit l'endroit d'où on lance Python.
AGENDA_FILE = Path(__file__).parent / "agenda.json"

# Créneaux de 30 minutes : 9h-12h le matin, 14h-18h l'après-midi
HEURES = ["09:00", "09:30", "10:00", "10:30", "11:00", "11:30",
          "14:00", "14:30", "15:00", "15:30", "16:00", "16:30", "17:00", "17:30"]

# Nombre de jours ouvrés (hors week-end) générés dans l'agenda
JOURS_A_GENERER = 14


# --- Gestion du fichier agenda ---------------------------------------------
def reinitialiser_agenda():
    """Crée un agenda pour les 14 prochains jours ouvrés, à moitié rempli.

    Chaque créneau est un dictionnaire :
        {"date": "2026-11-17", "heure": "09:00", "patient": None}
    patient = None signifie que le créneau est libre.
    """
    # Générateur aléatoire avec une graine fixe : il produit toujours la même suite de valeurs
    rng = random.Random(42)

    agenda = []
    jour = date.today()

    # On avance jour par jour jusqu'à avoir JOURS_A_GENERER jours différents
    while len({c["date"] for c in agenda}) < JOURS_A_GENERER:
        jour += timedelta(days=1)          # on commence à demain
        if jour.weekday() >= 5:            # weekday() : 0 = lundi ... 5 = samedi, 6 = dimanche
            continue                       # cabinet fermé le week-end : on saute ce jour

        for heure in HEURES:
            occupe = rng.random() < 0.5    # environ un créneau sur deux est déjà pris
            agenda.append({
                "date": jour.isoformat(),  # isoformat() : date au format "AAAA-MM-JJ"
                "heure": heure,
                "patient": "(déjà réservé)" if occupe else None,
            })

    _sauver(agenda)
    return agenda


def _charger():
    """Lit l'agenda depuis le fichier JSON (et le crée s'il n'existe pas).

    Le "_" au début du nom indique une fonction interne : elle n'est pas
    un outil proposé au LLM, seulement une aide pour nos outils.
    """
    if not AGENDA_FILE.exists():
        return reinitialiser_agenda()

    agenda = json.loads(AGENDA_FILE.read_text(encoding="utf-8"))

    # Si l'agenda a été créé un jour précédent, ses dates sont dépassées :
    # on en génère un nouveau à partir de la date du jour.
    if not agenda or agenda[0]["date"] <= date.today().isoformat():
        return reinitialiser_agenda()
    return agenda


def _sauver(agenda):
    """Écrit l'agenda dans le fichier JSON (indenté pour rester lisible)."""
    AGENDA_FILE.write_text(json.dumps(agenda, indent=2, ensure_ascii=False), encoding="utf-8")


def _verifier_date(date_str):
    """Vérifie qu'une date est utilisable pour un rendez-vous.

    Renvoie un message d'erreur (str) si la date pose problème, sinon None.
    """
    try:
        jour = date.fromisoformat(date_str)   # "2026-11-17" -> objet date
    except (TypeError, ValueError):           # pas une chaîne, ou format incorrect
        return f"Date invalide : '{date_str}'. Format attendu : AAAA-MM-JJ."
    if jour.weekday() >= 5:
        return "Le cabinet est fermé le week-end."
    if jour <= date.today():
        return "Les rendez-vous se prennent à partir de demain."
    return None  # aucune erreur


# --- Les outils -------------------------------------------------------------
# Les outils renvoient toujours un dictionnaire :
#   - en cas de succès : les données demandées (ou une confirmation) ;
#   - en cas de problème : {"erreur": "..."}.
# On ne lève pas d'exception : l'erreur est renvoyée sous forme de dictionnaire.

def chercher_creneaux(date):
    """Liste les créneaux libres d'une journée (date au format AAAA-MM-JJ)."""
    erreur = _verifier_date(date)
    if erreur:
        return {"erreur": erreur}

    # On garde les heures des créneaux de cette date dont le patient est None (libres)
    libres = [c["heure"] for c in _charger() if c["date"] == date and c["patient"] is None]
    return {"date": date, "creneaux_libres": libres}


def reserver_creneau(date, heure, nom):
    """Réserve un créneau libre au nom du patient."""
    erreur = _verifier_date(date)
    if erreur:
        return {"erreur": erreur}

    agenda = _charger()
    for creneau in agenda:
        if creneau["date"] == date and creneau["heure"] == heure:
            # Créneau trouvé : est-il encore libre ?
            if creneau["patient"] is not None:
                return {"erreur": f"Le créneau du {date} à {heure} est déjà pris."}
            creneau["patient"] = nom   # on inscrit le patient...
            _sauver(agenda)            # ...et on enregistre le fichier
            return {"confirmation": f"Rendez-vous réservé le {date} à {heure} pour {nom}."}

    # On a parcouru tout l'agenda sans trouver ce créneau (ex. heure "12:45")
    return {"erreur": f"Aucun créneau à {heure} le {date}."}


# --- Le catalogue d'outils ---------------------------------------------------
# Associe le NOM d'un outil (ce que le LLM écrira dans sa demande)
# à la FONCTION Python à exécuter. Le LLM ne connaît que les noms ;
# c'est ce dictionnaire qui fait le lien avec le vrai code.
OUTILS = {
    "chercher_creneaux": chercher_creneaux,
    "reserver_creneau": reserver_creneau,
}


# --- Démonstration (exécutée seulement si on lance ce fichier directement) ---
if __name__ == "__main__":
    # Option --reset : on remet l'agenda à neuf et on s'arrête là
    if "--reset" in sys.argv:
        reinitialiser_agenda()
        print("Agenda réinitialisé.")
        sys.exit()

    # On cherche le prochain jour ouvré (si demain est un samedi, on passe au lundi)
    demain = date.today() + timedelta(days=1)
    while demain.weekday() >= 5:
        demain += timedelta(days=1)

    # Cas normal, puis deux cas d'erreur
    print("chercher_creneaux :", chercher_creneaux(demain.isoformat()))
    print("week-end          :", chercher_creneaux("2026-11-21"))
    print("date invalide     :", chercher_creneaux("demain"))

    # On réserve le premier créneau libre, puis on essaie de le réserver une 2e fois
    libres = chercher_creneaux(demain.isoformat())["creneaux_libres"]
    if libres:
        print("reserver_creneau  :", reserver_creneau(demain.isoformat(), libres[0], "Test"))
        print("même créneau      :", reserver_creneau(demain.isoformat(), libres[0], "Autre"))

    # Réinitialise l'agenda modifié par la démo
    reinitialiser_agenda()
