"""
serveur_agenda_mcp.py
---------------------
Serveur MCP de l'agenda du cabinet, pour l'environnement CrewAI.

CrewAI utilise la version 1 du SDK MCP, dans laquelle le serveur s'appelle FastMCP.
Le principe est le même qu'avec MCPServer : chaque fonction décorée par @mcp.tool()
devient un outil, décrit par sa docstring et les types de ses paramètres.

Ce fichier n'est pas lancé à la main : CrewAI le démarre comme sous-processus
et dialogue avec lui par l'entrée / sortie standard (stdio).
"""

from typing import Annotated

from mcp.server.fastmcp import FastMCP
from pydantic import Field

import outils_cabinet

mcp = FastMCP(
    "agenda-cabinet",
    instructions="Outils de gestion de l'agenda du cabinet médical du Dr Martin.",
)

# Types réutilisés : la description de chaque paramètre est intégrée au schéma
Date = Annotated[str, Field(description="Date au format AAAA-MM-JJ.")]
Heure = Annotated[str, Field(description="Heure au format HH:MM (ex. 09:30).")]
Nom = Annotated[str, Field(description="Nom du patient.")]


@mcp.tool()
def chercher_creneaux(date: Date) -> dict:
    """Liste les créneaux libres du cabinet pour une journée donnée."""
    return outils_cabinet.chercher_creneaux(date)


@mcp.tool()
def lister_rdv(nom: Nom) -> dict:
    """Liste les rendez-vous déjà enregistrés au nom d'un patient."""
    return outils_cabinet.lister_rdv(nom)


@mcp.tool()
def reserver_creneau(date: Date, heure: Heure, nom: Nom) -> dict:
    """Réserve un créneau libre au nom d'un patient, après accord explicite du patient."""
    return outils_cabinet.reserver_creneau(date, heure, nom)


@mcp.tool()
def annuler_rdv(date: Date, heure: Heure, nom: Nom) -> dict:
    """Annule un rendez-vous existant d'un patient et libère le créneau."""
    return outils_cabinet.annuler_rdv(date, heure, nom)


@mcp.tool()
def deplacer_rdv(nom: Nom, ancienne_date: Date, ancienne_heure: Heure,
                 nouvelle_date: Date, nouvelle_heure: Heure) -> dict:
    """Déplace un rendez-vous existant vers un nouveau créneau
    (réserve le nouveau créneau avant d'annuler l'ancien)."""
    return outils_cabinet.deplacer_rdv(nom, ancienne_date, ancienne_heure, nouvelle_date, nouvelle_heure)


if __name__ == "__main__":
    # En mode stdio, aucun print() ne doit être fait : la sortie standard sert au protocole
    mcp.run(transport="stdio")
