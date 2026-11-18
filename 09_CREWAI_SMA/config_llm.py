"""
config_llm.py
-------------
Configuration des modèles utilisés par les agents CrewAI.

L'API NVIDIA est compatible OpenAI : on utilise le connecteur OpenAI de CrewAI
(préfixe "openai/" devant le nom du modèle) en lui donnant l'adresse de l'API NVIDIA.

Deux modèles sont proposés :
    - llm_agents      : utilisé par les agents spécialisés (rapide, raisonnement court)
    - llm_superviseur : utilisé par le manager dans le processus hiérarchique
                        (NVIDIA_THINKING_MODEL s'il est défini, sinon le même modèle)

Ce fichier n'est pas lancé directement : il est importé par les autres scripts du dossier.
"""

import os

from dotenv import load_dotenv

load_dotenv()

# Désactivation de la télémétrie envoyée par CrewAI (à faire avant d'importer crewai)
os.environ.setdefault("CREWAI_DISABLE_TELEMETRY", "true")
os.environ.setdefault("OTEL_SDK_DISABLED", "true")

from crewai import LLM  # noqa: E402  (import volontairement placé après la configuration)

URL_API = os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1")
CLE_API = os.getenv("NVIDIA_API_KEY")
MODELE = os.getenv("NVIDIA_MODEL", "mistralai/mistral-large-4-1t-a52b")
MODELE_SUPERVISEUR = os.getenv("NVIDIA_THINKING_MODEL") or MODELE
EFFORT = os.getenv("NVIDIA_REASONING_EFFORT", "low")

# Nombre maximum de requêtes par minute envoyées par une équipe (limite de l'API gratuite)
MAX_RPM = 30

# Taille de la fenêtre de contexte indiquée à CrewAI (sinon il suppose 8 192 tokens)
FENETRE_CONTEXTE = 32000

llm_agents = LLM(
    model=f"openai/{MODELE}",   # "openai/" : connecteur OpenAI de CrewAI
    base_url=URL_API,
    api_key=CLE_API,
    temperature=0,
    max_tokens=2048,
    reasoning_effort=EFFORT,
    timeout=120,
    context_window_size=FENETRE_CONTEXTE,
)

llm_superviseur = LLM(
    model=f"openai/{MODELE_SUPERVISEUR}",
    base_url=URL_API,
    api_key=CLE_API,
    temperature=0,
    max_tokens=4096,
    reasoning_effort="medium",
    timeout=180,
    context_window_size=FENETRE_CONTEXTE,
)
