"""
schemas_outils.py
-----------------
Description des outils au format attendu par l'API (format "tools" d'OpenAI).

À l'étape 02, les outils étaient décrits en texte libre dans le system prompt.
Ici, chaque outil est décrit par un schéma JSON structuré :
    - name        : nom de l'outil (doit correspondre à une clé de OUTILS)
    - description : à quoi sert l'outil (le modèle s'en sert pour choisir)
    - parameters  : les arguments attendus, leur type et leur description

Ce fichier est envoyé à l'API via le paramètre `tools=`.
"""

SCHEMAS_OUTILS = [
    {
        "type": "function",
        "function": {
            "name": "chercher_creneaux",
            "description": "Liste les créneaux libres du cabinet pour une journée donnée.",
            "parameters": {
                "type": "object",
                "properties": {
                    "date": {
                        "type": "string",
                        "description": "Date de la journée, au format AAAA-MM-JJ.",
                    },
                },
                # Arguments obligatoires
                "required": ["date"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "reserver_creneau",
            "description": (
                "Réserve un créneau libre au nom d'un patient. "
                "À utiliser uniquement après accord explicite du patient."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "date": {
                        "type": "string",
                        "description": "Date du rendez-vous, au format AAAA-MM-JJ.",
                    },
                    "heure": {
                        "type": "string",
                        "description": "Heure du créneau, au format HH:MM (ex. 09:30).",
                    },
                    "nom": {
                        "type": "string",
                        "description": "Nom du patient.",
                    },
                },
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
                "properties": {
                    "nom": {
                        "type": "string",
                        "description": "Nom du patient, tel qu'utilisé lors de la réservation.",
                    },
                },
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
                "properties": {
                    "date": {
                        "type": "string",
                        "description": "Date du rendez-vous, au format AAAA-MM-JJ.",
                    },
                    "heure": {
                        "type": "string",
                        "description": "Heure du rendez-vous, au format HH:MM.",
                    },
                    "nom": {
                        "type": "string",
                        "description": "Nom du patient.",
                    },
                },
                "required": ["date", "heure", "nom"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "deplacer_rdv",
            "description": (
                "Déplace un rendez-vous existant vers un nouveau créneau. "
                "Réserve le nouveau créneau avant d'annuler l'ancien."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "nom": {"type": "string", "description": "Nom du patient."},
                    "ancienne_date": {"type": "string", "description": "Date actuelle, AAAA-MM-JJ."},
                    "ancienne_heure": {"type": "string", "description": "Heure actuelle, HH:MM."},
                    "nouvelle_date": {"type": "string", "description": "Nouvelle date, AAAA-MM-JJ."},
                    "nouvelle_heure": {"type": "string", "description": "Nouvelle heure, HH:MM."},
                },
                "required": ["nom", "ancienne_date", "ancienne_heure", "nouvelle_date", "nouvelle_heure"],
            },
        },
    },
]
