"""
02_agent_mcp.py
---------------
La boucle agent de l'étape 04, branchée sur le serveur MCP.

Ce qui change :
    - plus de schemas_outils.py : les outils sont découverts auprès du serveur ;
    - plus d'import des fonctions Python : les outils sont exécutés par le serveur.

    patient ──> agent (LLM + boucle) ──── client MCP ────> serveur_agenda.py
                                     <── résultats ──────

Lancement :
    python 05_MCP/02_agent_mcp.py

Scénario à tester :
    Vous : Réservez-moi le premier créneau libre demain matin, je suis M. Leroy.
    Vous : Finalement, déplacez-le au dernier créneau libre de l'après-midi.

EXERCICES :
    1. Comparez le déplacement avec l'étape 04 : combien d'étapes ? Dans quel ordre ?
    2. Ajoutez un outil dans serveur_agenda.py. Faut-il modifier ce script ?
    3. Arrêtez-vous sur la fonction convertir_outil : à quoi sert-elle ?
    4. Tester dans un navigateur en lancant la commande :
        npx @modelcontextprotocol/inspector python 05_MCP/serveur_agenda.py
"""

import asyncio
import json
import os
import sys
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
MAX_ETAPES = 6

SERVEUR_AGENDA = StdioServerParameters(
    command=sys.executable,
    args=[str(Path(__file__).parent / "serveur_agenda.py")],
)

JOURS = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
aujourd_hui = date.today()

SYSTEM_PROMPT = f"""Tu es Doc'Assist, l'assistant de secrétariat du cabinet du Dr Martin.
Aujourd'hui, nous sommes le {JOURS[aujourd_hui.weekday()]} {aujourd_hui.isoformat()}.
Horaires : du lundi au vendredi, 9h-12h et 14h-18h.
Tu vouvoies le patient, ton ton est chaleureux et concis.
Tu ne donnes jamais de conseil médical.
N'invente jamais une disponibilité ni un rendez-vous : vérifie toujours avec les outils.
Pour déplacer un rendez-vous, utilise l'outil deplacer_rdv.
Ne réserve qu'après accord explicite du patient et quand tu connais son nom."""


# --- Passerelle MCP <-> API du LLM ---------------------------------------------
def convertir_outil(outil_mcp):
    """Convertit la description d'un outil MCP au format "tools" de l'API du LLM."""
    return {
        "type": "function",
        "function": {
            "name": outil_mcp.name,
            "description": outil_mcp.description or "",
            "parameters": outil_mcp.input_schema,
        },
    }


async def executer_outil_mcp(client_mcp, nom, arguments_json):
    """Demande au serveur MCP d'exécuter un outil et renvoie le résultat sous forme de texte."""
    try:
        arguments = json.loads(arguments_json or "{}")
    except json.JSONDecodeError:
        return f"Erreur : arguments non lisibles : {arguments_json}"

    try:
        resultat = await client_mcp.call_tool(nom, arguments)
    except Exception as e:  # outil inconnu, serveur arrêté...
        return f"Erreur lors de l'appel de {nom} : {e}"

    # Le résultat MCP est une liste de blocs de contenu : on garde les blocs texte
    texte = "\n".join(bloc.text for bloc in resultat.content if bloc.type == "text")
    return f"Erreur : {texte}" if resultat.is_error else texte


# --- Appel au LLM ------------------------------------------------------------
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


# --- La boucle agent (identique à l'étape 04, sauf l'exécution des outils) ----
async def executer_agent(client_mcp, outils, messages):
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
            print(f"   🔧 {nom}({tool_call.function.arguments})")
            # L'outil est exécuté par le serveur MCP, plus par notre programme
            resultat = await executer_outil_mcp(client_mcp, nom, tool_call.function.arguments)
            print(f"   📋 {resultat}")
            messages.append({"role": "tool", "tool_call_id": tool_call.id, "content": resultat})

    reponse = "Désolé, je n'ai pas réussi à traiter votre demande. Pouvez-vous la reformuler ?"
    print(f"   ⚠️  Limite de {MAX_ETAPES} étapes atteinte.")
    messages.append({"role": "assistant", "content": reponse})
    return reponse


# --- Programme principal -------------------------------------------------------
async def main():
    async with Client(SERVEUR_AGENDA) as client_mcp:
        # Découverte des outils puis conversion au format attendu par le LLM
        outils_mcp = (await client_mcp.list_tools()).tools
        outils = [convertir_outil(o) for o in outils_mcp]
        print(f"Connecté au serveur MCP : {[o.name for o in outils_mcp]}")
        print("Doc'Assist (agent MCP) — tapez 'exit' pour quitter.\n")

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
            reponse = await executer_agent(client_mcp, outils, messages)
            print(f"Doc'Assist : {reponse}\n")


asyncio.run(main())
