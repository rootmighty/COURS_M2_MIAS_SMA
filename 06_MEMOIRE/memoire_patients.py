"""
memoire_patients.py
-------------------
La mémoire longue de Doc'Assist : des informations sur chaque patient,
conservées d'une conversation à l'autre dans un fichier JSON.

Deux outils sont proposés à l'agent :
    - consulter_memoire(nom)                   : lire ce qu'on sait du patient
    - enregistrer_information(nom, information) : ajouter une information durable

Tester les fonctions seules :
    python 06_MEMOIRE/memoire_patients.py

Effacer toute la mémoire :
    python 06_MEMOIRE/memoire_patients.py --reset
"""

import json
import sys
from datetime import date
from pathlib import Path

FICHIER_MEMOIRE = Path(__file__).parent / "memoire_patients.json"


# --- Gestion du fichier ------------------------------------------------------
def _charger():
    if not FICHIER_MEMOIRE.exists():
        return {}
    return json.loads(FICHIER_MEMOIRE.read_text(encoding="utf-8"))


def _sauver(memoire):
    FICHIER_MEMOIRE.write_text(json.dumps(memoire, indent=2, ensure_ascii=False), encoding="utf-8")


def _cle(nom):
    """Clé du patient dans le fichier : nom en minuscules, sans espaces autour."""
    return nom.strip().lower()


# --- Les outils ---------------------------------------------------------------
def consulter_memoire(nom):
    """Renvoie les informations enregistrées sur un patient."""
    informations = _charger().get(_cle(nom), [])
    if not informations:
        return {"nom": nom, "informations": [], "remarque": "Aucune information enregistrée."}
    return {"nom": nom, "informations": informations}


def enregistrer_information(nom, information):
    """Ajoute une information durable sur un patient, datée du jour."""
    memoire = _charger()
    informations = memoire.setdefault(_cle(nom), [])

    # Pas de doublon : une information déjà présente n'est pas ajoutée
    if any(i["information"] == information for i in informations):
        return {"remarque": "Information déjà enregistrée."}

    informations.append({"information": information, "date": date.today().isoformat()})
    _sauver(memoire)
    return {"confirmation": f"Information enregistrée pour {nom}."}


# Catalogue et schémas des outils de mémoire
OUTILS_MEMOIRE = {
    "consulter_memoire": consulter_memoire,
    "enregistrer_information": enregistrer_information,
}

SCHEMAS_MEMOIRE = [
    {
        "type": "function",
        "function": {
            "name": "consulter_memoire",
            "description": "Consulte les informations enregistrées lors des conversations "
                           "précédentes avec un patient (préférences, habitudes).",
            "parameters": {
                "type": "object",
                "properties": {"nom": {"type": "string", "description": "Nom du patient."}},
                "required": ["nom"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "enregistrer_information",
            "description": "Enregistre une information durable et utile sur un patient pour les "
                           "prochaines conversations (préférence d'horaire, de médecin, de contact). "
                           "Jamais d'information médicale.",
            "parameters": {
                "type": "object",
                "properties": {
                    "nom": {"type": "string", "description": "Nom du patient."},
                    "information": {"type": "string",
                                    "description": "L'information à retenir, en une phrase courte."},
                },
                "required": ["nom", "information"],
            },
        },
    },
]


if __name__ == "__main__":
    if "--reset" in sys.argv:
        FICHIER_MEMOIRE.unlink(missing_ok=True)
        print("Mémoire effacée.")
        sys.exit()

    print(enregistrer_information("Mme Dubois", "Préfère les rendez-vous le matin."))
    print(enregistrer_information("Mme Dubois", "Préfère les rendez-vous le matin."))
    print(consulter_memoire("mme dubois"))
    print(consulter_memoire("M. Inconnu"))
    FICHIER_MEMOIRE.unlink(missing_ok=True)
