"""
04_agent_multi_serveurs.py
--------------------------
Un agent connecté à DEUX serveurs MCP à la fois :
    - notre serveur agenda (local, lancé en sous-processus) ;
    - le serveur data.gouv.fr (distant, par URL).

L'agent reçoit la liste de tous les outils, sans savoir d'où ils viennent.
Notre programme garde en mémoire quel serveur possède quel outil,
pour envoyer chaque appel au bon endroit.

                         ┌── client MCP ──> serveur_agenda.py   (local)
    patient ──> agent ───┤
                         └── client MCP ──> mcp.data.gouv.fr     (distant)

Lancement :
    python 05_MCP/04_agent_multi_serveurs.py

Questions à tester :
    Vous : Existe-t-il des données publiques sur les pharmacies en France ?
    Vous : Merci. Et il vous reste de la place demain matin ? Je suis Mme Dubois.

EXERCICES :
    1. Pour chaque question, quels outils l'agent choisit-il ? Pourquoi ?
    2. Combien d'outils l'agent reçoit-il au total ? Quel impact sur le prompt et le coût ?
    3. Les données renvoyées par data.gouv.fr sont tronquées (MAX_CARACTERES).
       Pourquoi ? Que se passe-t-il si on augmente beaucoup cette valeur ?
"""

import asyncio
import json
import os
import sys
from contextlib import AsyncExitStack
from datetime import date
from pathlib import Path

from dotenv import load_dotenv
from mcp import Client, StdioServerParameters
from openai import OpenAI

load_dotenv()

# --- Configuration ---------------------------------------------------------
client_llm = OpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=os.getenv("NVIDIA_API_KEY"),
    max_retries=3,
    timeout=60,
)
MODEL = os.getenv("NVIDIA_MODEL", "mistralai/mistral-large-4-1t-a52b")
REASONING_EFFORT = os.getenv("NVIDIA_REASONING_EFFORT", "low")
MAX_ETAPES = 8

# Taille maximale d'un résultat d'outil envoyé au LLM
MAX_CARACTERES = 3000

# Les serveurs auxquels se connecter : nom -> paramètres de connexion
SERVEURS = {
    "agenda": StdioServerParameters(
        command=sys.executable,
        args=[str(Path(__file__).parent / "serveur_agenda.py")],
    ),
    "datagouv": "https://mcp.data.gouv.fr/mcp",
}

JOURS = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
aujourd_hui = date.today()

SYSTEM_PROMPT = f"""Tu es Doc'Assist, l'assistant de secrétariat du cabinet du Dr Martin (Lille).
Aujourd'hui, nous sommes le {JOURS[aujourd_hui.weekday()]} {aujourd_hui.isoformat()}.
Horaires : du lundi au vendredi, 9h-12h et 14h-18h.
Tu vouvoies le patient, ton ton est chaleureux et concis.
Tu ne donnes jamais de conseil médical.
Tu disposes d'outils pour gérer l'agenda du cabinet, et d'outils pour consulter
les données publiques de data.gouv.fr. Cite toujours la source des données publiques.
N'invente jamais une disponibilité ni une donnée : vérifie toujours avec les outils.
Ne réserve qu'après accord explicite du patient et quand tu connais son nom."""


def message_erreur(e):
    """Renvoie le message de la première erreur réelle (les erreurs réseau
    arrivent parfois regroupées dans un ExceptionGroup)."""
    while isinstance(e, BaseExceptionGroup) and e.exceptions:
        e = e.exceptions[0]
    return f"{type(e).__name__} : {e}"


# --- Passerelle MCP <-> API du LLM ---------------------------------------------
def convertir_outil(outil_mcp):
    """Convertit la description d'un outil MCP au format "tools" de l'API du LLM."""
    return {
        "type": "function",
        "function": {
            "name": outil_mcp.name,
            "description": (outil_mcp.description or "")[:1000],
            "parameters": outil_mcp.input_schema,
        },
    }


async def executer_outil_mcp(client_mcp, nom, arguments_json):
    """Demande au serveur MCP d'exécuter un outil et renvoie le résultat (texte tronqué)."""
    try:
        arguments = json.loads(arguments_json or "{}")
    except json.JSONDecodeError:
        return f"Erreur : arguments non lisibles : {arguments_json}"
    try:
        resultat = await client_mcp.call_tool(nom, arguments)
    except Exception as e:
        return f"Erreur lors de l'appel de {nom} : {e}"

    texte = "\n".join(bloc.text for bloc in resultat.content if bloc.type == "text")
    if resultat.is_error:
        texte = f"Erreur : {texte}"
    # Troncature des résultats trop longs
    if len(texte) > MAX_CARACTERES:
        texte = texte[:MAX_CARACTERES] + "\n[... résultat tronqué]"
    return texte


def appeler_llm(messages, outils):
    completion = client_llm.chat.completions.create(
        model=MODEL,
        messages=messages,
        tools=outils,
        tool_choice="auto",
        max_tokens=1024,
        temperature=0,
        reasoning_effort=REASONING_EFFORT,
    )
    return completion.choices[0].message


# --- La boucle agent -------------------------------------------------------------
async def executer_agent(routage, outils, messages):
    """Boucle agent. `routage` associe chaque nom d'outil au client MCP qui le possède."""
    for etape in range(1, MAX_ETAPES + 1):
        print(f"   ── Étape {etape} ──")
        message = appeler_llm(messages, outils)

        if not message.tool_calls:
            reponse = message.content or "(pas de réponse texte)"
            messages.append({"role": "assistant", "content": reponse})
            return reponse

        messages.append({
            "role": "assistant",
            "content": message.content,
            "tool_calls": [tc.model_dump() for tc in message.tool_calls],
        })
        for tool_call in message.tool_calls:
            nom = tool_call.function.name
            if nom in routage:
                nom_serveur, client_mcp = routage[nom]
                print(f"   🔧 [{nom_serveur}] {nom}({tool_call.function.arguments})")
                resultat = await executer_outil_mcp(client_mcp, nom, tool_call.function.arguments)
            else:
                resultat = f"Erreur : outil inconnu '{nom}'."
            # Aperçu court dans le terminal (le LLM reçoit le résultat complet)
            print(f"   📋 {resultat[:200]}{'...' if len(resultat) > 200 else ''}")
            messages.append({"role": "tool", "tool_call_id": tool_call.id, "content": resultat})

    reponse = "Désolé, je n'ai pas réussi à traiter votre demande. Pouvez-vous la reformuler ?"
    print(f"   ⚠️  Limite de {MAX_ETAPES} étapes atteinte.")
    messages.append({"role": "assistant", "content": reponse})
    return reponse


# --- Programme principal -------------------------------------------------------
async def main():
    # AsyncExitStack garde plusieurs connexions ouvertes et les ferme toutes à la fin
    async with AsyncExitStack() as pile:
        routage = {}   # nom de l'outil -> (nom du serveur, client MCP)
        outils = []    # liste des outils au format du LLM

        for nom_serveur, connexion in SERVEURS.items():
            try:
                client_mcp = await pile.enter_async_context(Client(connexion))
                outils_mcp = (await client_mcp.list_tools()).tools
            except Exception as e:
                # Un serveur indisponible ne bloque pas l'agent : on continue sans lui
                print(f"⚠️  Serveur '{nom_serveur}' indisponible : {message_erreur(e)}")
                continue

            print(f"Connecté à '{nom_serveur}' : {[o.name for o in outils_mcp]}")
            for outil in outils_mcp:
                routage[outil.name] = (nom_serveur, client_mcp)
                outils.append(convertir_outil(outil))

        print(f"\n{len(outils)} outils disponibles au total.")
        print("Doc'Assist (multi-serveurs) — tapez 'exit' pour quitter.\n")

        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        while True:
            try:
                question = input("Vous : ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                break
            if question.lower() in {"exit", "quit"}:
                break
            if not question:
                continue

            messages.append({"role": "user", "content": question})
            reponse = await executer_agent(routage, outils, messages)
            print(f"Doc'Assist : {reponse}\n")


asyncio.run(main())
