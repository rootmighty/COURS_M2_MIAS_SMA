"""
01_inspecter_serveur.py
-----------------------
Un client MCP minimal, sans IA : se connecter au serveur, découvrir ses outils, en appeler un.

Le client ne connaît rien des outils à l'avance : il les DÉCOUVRE en interrogeant
le serveur (list_tools). C'est ce que fera notre agent à l'étape suivante.

Lancement :
    python 05_MCP/01_inspecter_serveur.py

EXERCICES :
    1. Comparez les schémas affichés avec ceux écrits à la main dans 04_BOUCLE_AGENT/schemas_outils.py.
    2. Ajoutez un outil "horaires_cabinet()" dans serveur_agenda.py, sans toucher à ce script.
       Apparaît-il ici ?
    3. Appelez reserver_creneau sans le paramètre "nom". Quelle réponse renvoie le serveur ?
"""

import asyncio
import json
import sys
from datetime import date, timedelta
from pathlib import Path

from mcp import Client, StdioServerParameters

# Commande de lancement du serveur : le client le démarre lui-même en sous-processus.
# sys.executable = l'interpréteur Python en cours (celui du .venv).
SERVEUR_AGENDA = StdioServerParameters(
    command=sys.executable,
    args=[str(Path(__file__).parent / "serveur_agenda.py")],
)


def texte_du_resultat(resultat):
    """Assemble les blocs de texte d'un résultat d'outil MCP."""
    return "\n".join(bloc.text for bloc in resultat.content if bloc.type == "text")


async def main():
    # "async with" ouvre la connexion au serveur et la ferme automatiquement à la fin
    async with Client(SERVEUR_AGENDA) as client:

        # 1. Découverte des outils proposés par le serveur
        reponse = await client.list_tools()
        print(f"Le serveur propose {len(reponse.tools)} outils :\n")
        for outil in reponse.tools:
            print(f"🔧 {outil.name}")
            print(f"   Description : {outil.description}")
            print(f"   Schéma      : {json.dumps(outil.input_schema, ensure_ascii=False)}\n")

        # Prochain jour ouvré
        jour = date.today() + timedelta(days=1)
        while jour.weekday() >= 5:
            jour += timedelta(days=1)

        # 2. Appel direct d'un outil (aucun LLM)
        print("=" * 70)
        resultat = await client.call_tool("chercher_creneaux", {"date": jour.isoformat()})
        print(f"chercher_creneaux -> erreur : {resultat.is_error}")
        print(texte_du_resultat(resultat))

        # 3. Appel avec des arguments invalides : le serveur les vérifie lui-même
        print("=" * 70)
        resultat = await client.call_tool("chercher_creneaux", {})
        print(f"chercher_creneaux sans date -> erreur : {resultat.is_error}")
        print(texte_du_resultat(resultat))
        


# asyncio.run lance la fonction asynchrone main()
asyncio.run(main())
