"""
serveur_agenda.py
-----------------
Un serveur MCP qui expose les outils de l'agenda du cabinet.

MCP (Model Context Protocol) est un protocole standard pour connecter des outils
à n'importe quel agent ou application d'IA. Au lieu d'écrire les schémas JSON à la
main (étape 03), on déclare des fonctions Python : le SDK génère les schémas
à partir des types et des descriptions.

Ce serveur ne contient AUCUNE IA. Il attend des requêtes d'un client MCP
(notre agent, Claude Desktop, un IDE...) et exécute les outils demandés.

Ce fichier n'est pas lancé à la main : le client le démarre lui-même
comme sous-processus, et dialogue avec lui par l'entrée / sortie standard (stdio).

Prérequis :
    pip install mcp

Test avec l'inspecteur officiel (interface web, nécessite Node.js) :
    npx @modelcontextprotocol/inspector python 05_MCP/serveur_agenda.py
"""

from typing import Annotated

from mcp.server.mcpserver import MCPServer
from pydantic import Field

import outils_cabinet

# Création du serveur, avec son nom et des instructions destinées aux clients
mcp = MCPServer(
    "agenda-cabinet",
    instructions="Outils de gestion de l'agenda du cabinet médical du Dr Martin.",
)

# Types réutilisés : Annotated associe à chaque paramètre une description,
# qui sera intégrée au schéma JSON envoyé au client.
Date = Annotated[str, Field(description="Date au format AAAA-MM-JJ.")]
Heure = Annotated[str, Field(description="Heure au format HH:MM (ex. 09:30).")]
Nom = Annotated[str, Field(description="Nom du patient.")]


# --- Les outils ---------------------------------------------------------------
# @mcp.tool() enregistre la fonction comme outil MCP :
#   - le nom de la fonction devient le nom de l'outil ;
#   - la docstring devient sa description ;
#   - les paramètres et leurs types deviennent le schéma des arguments.

@mcp.tool()
def chercher_creneaux(date: Date) -> dict:
    """Liste les créneaux libres du cabinet pour une journée donnée."""
    return outils_cabinet.chercher_creneaux(date)


@mcp.tool()
def reserver_creneau(date: Date, heure: Heure, nom: Nom) -> dict:
    """Réserve un créneau libre au nom d'un patient. À utiliser uniquement après accord du patient."""
    return outils_cabinet.reserver_creneau(date, heure, nom)


@mcp.tool()
def lister_rdv(nom: Nom) -> dict:
    """Liste les rendez-vous déjà enregistrés au nom d'un patient."""
    return outils_cabinet.lister_rdv(nom)


@mcp.tool()
def annuler_rdv(date: Date, heure: Heure, nom: Nom) -> dict:
    """Annule un rendez-vous existant d'un patient et libère le créneau."""
    return outils_cabinet.annuler_rdv(date, heure, nom)


@mcp.tool()
def deplacer_rdv(
    nom: Nom,
    ancienne_date: Date,
    ancienne_heure: Heure,
    nouvelle_date: Date,
    nouvelle_heure: Heure,
) -> dict:
    """Déplace un rendez-vous existant vers un nouveau créneau.
    Réserve le nouveau créneau avant d'annuler l'ancien : en cas d'échec, rien n'est perdu."""
    return outils_cabinet.deplacer_rdv(nom, ancienne_date, ancienne_heure, nouvelle_date, nouvelle_heure)


if __name__ == "__main__":
    # Démarrage du serveur en mode stdio (dialogue par l'entrée / sortie standard).
    # Attention : en mode stdio, aucun print() ne doit être fait dans les outils,
    # car la sortie standard est réservée aux messages du protocole.
    mcp.run(transport="stdio")
