"""
02_avec_sdk_openai.py
---------------------
Le même appel qu'en 01, mais avec le SDK officiel `openai`.

L'API NVIDIA est "compatible OpenAI" : il suffit de changer `base_url`.
C'est ce mécanisme qu'utiliseront plus tard les frameworks comme CrewAI.

Bonus : le SDK gère tout seul les réessais sur les erreurs 429 et 5xx
(paramètre `max_retries`).

Prérequis :
    pip install openai

Lancement :
    python 00_LLM_CALL/02_avec_sdk_openai.py
"""

import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(
    base_url="https://integrate.api.nvidia.com/v1",  # seule différence avec OpenAI
    api_key=os.getenv("NVIDIA_API_KEY"),
    max_retries=3,  # réessais automatiques en cas de 429 / erreur serveur
    timeout=60,
)

completion = client.chat.completions.create(
    model=os.getenv("NVIDIA_MODEL", "mistralai/mistral-large-4-1t-a52b"),
    messages=[{"role": "user", "content": "Bonjour, je voudrais prendre un rendez-vous."}],
    max_tokens=1024,  # raisonnement + réponse
    temperature=0.5,
    reasoning_effort=os.getenv("NVIDIA_REASONING_EFFORT", "low"),  # réflexion courte
)

# Le SDK transforme le JSON en objets Python : plus besoin de ["choices"][0]...
choice = completion.choices[0]
print(choice.message.content or "(vide)")
print(f"\nFin de génération : {choice.finish_reason}")
print(f"Tokens consommés : {completion.usage.total_tokens}")
