"""
01b_modele_thinking.py
----------------------
Le piège des modèles "thinking" (qui raisonnent avant de répondre).

On pose la MÊME question au même modèle, trois fois :
    1. effort "high", max_tokens = 300   -> le raisonnement mange tout le budget
    2. effort "high", max_tokens = 2048  -> le modèle a le temps de répondre
    3. effort "low",  max_tokens = 2048  -> réflexion courte : plus rapide, moins cher

À observer dans chaque cas :
    - message.reasoning_content : le raisonnement, dans un champ séparé
    - message.content           : la réponse (peut être None !)
    - finish_reason             : "stop" (terminé) ou "length" (coupé)
    - usage.completion_tokens_details.reasoning_tokens : coût du raisonnement
    - la durée de l'appel

Modèle utilisé : NVIDIA_THINKING_MODEL si renseigné, sinon NVIDIA_MODEL.

Lancement :
    python 00_LLM_CALL/01b_modele_thinking.py
"""

import os
import sys
import time

import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("NVIDIA_API_KEY")
MODEL = os.getenv("NVIDIA_THINKING_MODEL") or os.getenv("NVIDIA_MODEL")
URL = "https://integrate.api.nvidia.com/v1/chat/completions"
QUESTION = "Bonjour, je voudrais prendre un rendez-vous."

if not MODEL:
    sys.exit("Aucun modèle : renseignez NVIDIA_THINKING_MODEL ou NVIDIA_MODEL dans le .env")


def appel(effort, max_tokens):
    """Pose la question avec un effort de raisonnement et une limite donnés."""
    print(f"\n{'=' * 60}\nreasoning_effort = {effort} | max_tokens = {max_tokens}\n{'=' * 60}")

    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": QUESTION}],
        "max_tokens": max_tokens,
        "temperature": 0.5,
        "reasoning_effort": effort,
    }
    debut = time.perf_counter()
    response = requests.post(
        URL, headers={"Authorization": f"Bearer {API_KEY}"}, json=payload, timeout=120
    )
    duree = time.perf_counter() - debut
    if not response.ok:
        print(f"Erreur HTTP {response.status_code} : {response.text}")
        return

    data = response.json()
    choice = data["choices"][0]
    message = choice["message"]
    usage = data["usage"]
    reasoning_tokens = (usage.get("completion_tokens_details") or {}).get("reasoning_tokens", 0)

    reasoning = message.get("reasoning_content") or ""
    print(f"\n[Raisonnement] ({len(reasoning)} caractères)")
    print(reasoning[:400] + ("..." if len(reasoning) > 400 else ""))

    print("\n[Réponse]")
    print(message.get("content") or "None  <-- aucune réponse !")

    print(f"\nfinish_reason : {choice['finish_reason']}")
    print(f"Tokens en sortie : {usage['completion_tokens']} "
          f"(dont {reasoning_tokens} de raisonnement)")
    print(f"Durée : {duree:.1f} s")
    if choice["finish_reason"] == "length":
        print("⚠️  Coupé par max_tokens : le budget est parti dans le raisonnement.")


appel(effort="high", max_tokens=300)
appel(effort="high", max_tokens=2048)
appel(effort="low", max_tokens=2048)
