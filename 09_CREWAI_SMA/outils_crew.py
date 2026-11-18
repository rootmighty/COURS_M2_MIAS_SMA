"""
outils_crew.py
--------------
Les outils de Doc'Assist au format CrewAI.

Le décorateur @tool transforme une fonction Python en outil utilisable par un agent :
    - le nom passé au décorateur devient le nom de l'outil ;
    - la docstring devient sa description (le modèle s'en sert pour choisir) ;
    - les paramètres et leurs types deviennent le schéma des arguments.

Les outils appellent les fonctions de outils_cabinet.py (agenda) et de rag.py (documents),
et renvoient leur résultat sous forme de texte JSON.

Ce fichier n'est pas lancé directement : il est importé par les autres scripts du dossier.
"""

import json

from crewai.tools import tool

import outils_cabinet as agenda
from rag import rechercher


def en_texte(resultat):
    """Convertit un résultat (dictionnaire) en texte JSON lisible par le modèle."""
    return json.dumps(resultat, ensure_ascii=False)


# --- Outils de l'agenda ----------------------------------------------------------
@tool("chercher_creneaux")
def chercher_creneaux(date: str) -> str:
    """Liste les créneaux libres du cabinet pour une journée. date : format AAAA-MM-JJ."""
    return en_texte(agenda.chercher_creneaux(date))


@tool("lister_rdv")
def lister_rdv(nom: str) -> str:
    """Liste les rendez-vous déjà enregistrés au nom d'un patient."""
    return en_texte(agenda.lister_rdv(nom))


@tool("reserver_creneau")
def reserver_creneau(date: str, heure: str, nom: str) -> str:
    """Réserve un créneau libre. date : AAAA-MM-JJ, heure : HH:MM, nom : nom du patient.
    À utiliser uniquement après accord explicite du patient."""
    return en_texte(agenda.reserver_creneau(date, heure, nom))


# --- Outil de recherche documentaire ----------------------------------------------
@tool("rechercher_documents")
def rechercher_documents(requete: str) -> str:
    """Recherche dans les documents du cabinet (horaires, accès, tarifs, remboursements,
    téléconsultation, visites à domicile, absences, urgences, données personnelles,
    règles d'annulation et de retard). requete : une phrase courte et précise."""
    resultats = rechercher(requete, k=3)
    return en_texte([
        {"source": f"{r['source']} — {r['section']}", "extrait": r["texte"], "score": r["score"]}
        for r in resultats
    ])
