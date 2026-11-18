"""
03_inspecter_datagouv.py
------------------------
Se connecter à un serveur MCP distant : celui de data.gouv.fr.

Le serveur officiel de data.gouv.fr permet d'explorer les données publiques
françaises (en lecture seule, sans clé API). Il est hébergé sur Internet :
on s'y connecte par une simple URL (transport "Streamable HTTP"),
au lieu de lancer un sous-processus comme pour notre serveur agenda.

Le code client est le même : seule la façon de se connecter change.

Lancement :
    python 05_MCP/03_inspecter_datagouv.py

Attention : ce serveur est expérimental. S'il ne répond pas, réessayez plus tard.
Méfiez-vous des serveurs qui se disent liés à data.gouv.fr sans être officiels :
un serveur MCP exécute du code et renvoie du contenu lu par votre agent.

EXERCICES :
    1. Quels outils propose le serveur ? Lequel utiliseriez-vous pour trouver
       la liste des pharmacies en France ?
    2. Changez RECHERCHE pour chercher un autre jeu de données de santé.
    3. Le résultat est-il court ou long ? Quel problème cela pose-t-il pour un agent ?
"""

import asyncio
import json

from mcp import Client

URL_DATAGOUV = "https://mcp.data.gouv.fr/mcp"
RECHERCHE = "pharmacies"  # ou "pharmacies", "vaccination", "covid", "cancer", "diabetes"...


def message_erreur(e):
    """Renvoie le message de la première erreur réelle (les erreurs réseau
    arrivent parfois regroupées dans un ExceptionGroup)."""
    while isinstance(e, BaseExceptionGroup) and e.exceptions:
        e = e.exceptions[0]
    return f"{type(e).__name__} : {e}"


def texte_du_resultat(resultat):
    """Assemble les blocs de texte d'un résultat d'outil MCP."""
    return "\n".join(bloc.text for bloc in resultat.content if bloc.type == "text")


async def main():
    # Connexion par URL : le client utilise le transport Streamable HTTP
    async with Client(URL_DATAGOUV) as client:
        outils = (await client.list_tools()).tools
        print(f"Le serveur data.gouv.fr propose {len(outils)} outils :\n")
        for outil in outils:
            print(f"🔧 {outil.name}")
            print(f"   {(outil.description or '').strip()[:200]}")
            print(f"   Paramètres : {list(outil.input_schema.get('properties', {}))}\n")

        # Appel de l'outil de recherche de jeux de données.
        # Le nom du paramètre texte est lu dans le schéma (premier paramètre obligatoire).
        recherche = next((o for o in outils if o.name == "search_datasets"), None)
        if recherche is None:
            print("Outil search_datasets introuvable.")
            return
        parametre = recherche.input_schema.get("required", ["query"])[0]

        print("=" * 70)
        print(f"search_datasets({parametre}={RECHERCHE!r})\n")
        resultat = await client.call_tool("search_datasets", {parametre: RECHERCHE})
        texte = texte_du_resultat(resultat)
        print(texte[:2000])
        print(f"\n[{len(texte)} caractères au total]")


try:
    asyncio.run(main())
except Exception as e:
    print(f"Impossible de joindre le serveur data.gouv.fr : {message_erreur(e)}")
