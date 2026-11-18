"""
01_premier_appel.py
-------------------
Le tout premier appel à un LLM : une question, une réponse.

Pas de streaming, pas d'historique : on envoie une requête HTTP
et on affiche la réponse JSON BRUTE pour voir ce que renvoie l'API.

Modèle utilisé : NVIDIA_MODEL (un modèle "classique", sans raisonnement).
Pour les modèles "thinking", voir 01b_modele_thinking.py.

Lancement :
    python 00_LLM_CALL/01_premier_appel.py
"""

import json
import os

import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("NVIDIA_API_KEY")
MODEL = os.getenv("NVIDIA_MODEL", "mistralai/mistral-large-4-1t-a52b")
REASONING_EFFORT = os.getenv("NVIDIA_REASONING_EFFORT", "low")  # low | medium | high
URL = "https://integrate.api.nvidia.com/v1/chat/completions"

# 1. La requête : qui on est (en-tête) + ce qu'on demande (payload)
headers = {"Authorization": f"Bearer {API_KEY}"}
payload = {
    "model": MODEL,
    "messages": [{"role": "user", "content": "Bonjour, je voudrais prendre un rendez-vous."}],
    "max_tokens": 1024,    # longueur maximale (raisonnement + réponse)
    "temperature": 0.5,    # créativité : 0 = déterministe, plus haut = plus varié
    # Les modèles récents "réfléchissent" avant de répondre.
    # "low" = réflexion courte : plus rapide et moins de tokens consommés.
    "reasoning_effort": REASONING_EFFORT,
}

# 2. L'appel HTTP
response = requests.post(URL, headers=headers, json=payload, timeout=60)

# 3. La réponse brute : observez "choices", "usage", "model"...
print(f"Code HTTP : {response.status_code}\n")
print(json.dumps(response.json(), indent=2, ensure_ascii=False))

# 4. Ce qui nous intéresse vraiment : le texte généré
if response.ok:
    data = response.json()
    choice = data["choices"][0]

    print("\n--- Réponse du modèle ---")
    print(choice["message"].get("content") or "(vide)")

    # finish_reason : "stop" = réponse terminée, "length" = coupée par max_tokens
    print(f"\nFin de génération : {choice['finish_reason']}")
    usage = data["usage"]
    reasoning = (usage.get("completion_tokens_details") or {}).get("reasoning_tokens", 0)
    print(f"Tokens : {usage['prompt_tokens']} en entrée, "
          f"{usage['completion_tokens']} en sortie (dont {reasoning} de raisonnement)")
