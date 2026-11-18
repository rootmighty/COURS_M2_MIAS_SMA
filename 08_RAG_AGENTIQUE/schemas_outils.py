"""
schemas_outils.py
-----------------
Description des outils au format attendu par l'API (paramètre `tools=`).

Chaque outil est décrit par :
    - name        : nom de l'outil (doit correspondre à une clé de OUTILS)
    - description : à quoi sert l'outil (le modèle s'en sert pour choisir)
    - parameters  : les arguments attendus, leur type et leur description
"""

# Paramètres réutilisés dans plusieurs outils
DATE = {"type": "string", "description": "Date au format AAAA-MM-JJ."}
HEURE = {"type": "string", "description": "Heure au format HH:MM (ex. 09:30)."}
NOM = {"type": "string", "description": "Nom du patient."}

SCHEMAS_OUTILS = [
    {
        "type": "function",
        "function": {
            "name": "chercher_creneaux",
            "description": "Liste les créneaux libres du cabinet pour une journée donnée.",
            "parameters": {
                "type": "object",
                "properties": {"date": DATE},
                "required": ["date"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "reserver_creneau",
            "description": "Réserve un créneau libre au nom d'un patient. "
                           "À utiliser uniquement après accord explicite du patient.",
            "parameters": {
                "type": "object",
                "properties": {"date": DATE, "heure": HEURE, "nom": NOM},
                "required": ["date", "heure", "nom"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "lister_rdv",
            "description": "Liste les rendez-vous déjà enregistrés au nom d'un patient.",
            "parameters": {
                "type": "object",
                "properties": {"nom": NOM},
                "required": ["nom"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "annuler_rdv",
            "description": "Annule un rendez-vous existant d'un patient et libère le créneau.",
            "parameters": {
                "type": "object",
                "properties": {"date": DATE, "heure": HEURE, "nom": NOM},
                "required": ["date", "heure", "nom"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "deplacer_rdv",
            "description": "Déplace un rendez-vous existant vers un nouveau créneau. "
                           "Réserve le nouveau créneau avant d'annuler l'ancien.",
            "parameters": {
                "type": "object",
                "properties": {
                    "nom": NOM,
                    "ancienne_date": {**DATE, "description": "Date actuelle du rendez-vous, AAAA-MM-JJ."},
                    "ancienne_heure": {**HEURE, "description": "Heure actuelle du rendez-vous, HH:MM."},
                    "nouvelle_date": {**DATE, "description": "Nouvelle date, AAAA-MM-JJ."},
                    "nouvelle_heure": {**HEURE, "description": "Nouvelle heure, HH:MM."},
                },
                "required": ["nom", "ancienne_date", "ancienne_heure", "nouvelle_date", "nouvelle_heure"],
            },
        },
    },
]
