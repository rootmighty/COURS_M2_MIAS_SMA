"""
02_sortie_json.py
-----------------
Transformer du texte libre en données structurées (JSON) exploitables par le code.

Un patient écrit en langage naturel : "Je voudrais voir le docteur mardi prochain
le matin pour un renouvellement d'ordonnance". Le programme, lui, a besoin de
champs précis (nom, motif, date...) pour chercher un créneau.

Étapes :
    1. On décrit le format attendu avec un modèle Pydantic.
    2. On demande au LLM de répondre UNIQUEMENT en JSON respectant ce schéma.
    3. On VALIDE la réponse : un LLM peut se tromper (champ manquant, mauvais format...).
    4. Si la validation échoue, on renvoie l'erreur au modèle pour qu'il se corrige.

Lancement :
    python 01_PROMPTS_ET_SORTIES/02_sortie_json.py

EXERCICES :
    1. Ajoutez un champ "telephone" au schéma. Que faut-il modifier d'autre ?
    2. Écrivez un message ambigu ("je passerai un de ces jours"). Que renvoie le modèle ?
    3. Retirez l'étape de validation : quels risques pour la suite du programme ?
"""

import json
import os
from datetime import date
from typing import Literal, Optional

from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel, Field, ValidationError

load_dotenv()

# --- Configuration ---------------------------------------------------------
client = OpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=os.getenv("NVIDIA_API_KEY"),
    max_retries=3,
    timeout=60,
)
MODEL = os.getenv("NVIDIA_MODEL", "mistralai/mistral-large-4-1t-a52b")
REASONING_EFFORT = os.getenv("NVIDIA_REASONING_EFFORT", "low")
MAX_CORRECTIONS = 2   # nombre de fois où l'on laisse le modèle corriger sa réponse


# --- 1. Le format attendu ----------------------------------------------------
# Pydantic permet de décrire une structure de données avec des types.
# Il sert ici à deux choses :
#   - générer un schéma JSON qu'on montre au modèle (ce qu'on attend) ;
#   - vérifier que la réponse du modèle respecte bien ce format.
class DemandeRDV(BaseModel):
    """Informations extraites d'une demande de rendez-vous."""

    # Optional[str] = une chaîne OU None (si l'information n'est pas dans le message)
    # Field(..., description=...) : la description est incluse dans le schéma JSON,
    # elle aide le modèle à comprendre ce qu'on attend dans chaque champ.
    nom: Optional[str] = Field(None, description="Nom du patient, null si non mentionné")
    motif: Optional[str] = Field(None, description="Motif de la consultation, en quelques mots")

    # Type date : Pydantic convertit "2026-11-17" en objet date, et refuse "mardi"
    date_souhaitee: Optional[date] = Field(
        None, description="Date souhaitée au format AAAA-MM-JJ, null si non mentionnée"
    )

    # Literal : seules ces deux valeurs exactes sont acceptées ("après-midi" avec accent sera refusé)
    creneau: Optional[Literal["matin", "apres-midi"]] = Field(
        None, description="Moment de la journée souhaité, null si non mentionné"
    )
    nouveau_patient: Optional[bool] = Field(
        None, description="true si le patient dit venir pour la première fois"
    )


# --- 2. Le prompt d'extraction -------------------------------------------------
JOURS = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
aujourd_hui = date.today()

# Date du jour (avec le nom du jour) pour interpréter "demain", "mardi prochain"...
# model_json_schema() génère automatiquement le schéma JSON à partir de la classe Pydantic.
SYSTEM_PROMPT = f"""Tu es un module d'extraction d'informations pour le secrétariat d'un cabinet médical.
Aujourd'hui, nous sommes le {JOURS[aujourd_hui.weekday()]} {aujourd_hui.isoformat()}.

À partir du message du patient, extrais les informations de la demande de rendez-vous.
Réponds UNIQUEMENT avec un objet JSON valide, sans texte autour, sans balises markdown,
qui respecte ce schéma :

{json.dumps(DemandeRDV.model_json_schema(), indent=2, ensure_ascii=False)}

Si une information n'est pas présente dans le message, mets null. N'invente rien."""

# Messages de patients à analyser
MESSAGES_PATIENTS = [
    "Bonjour, c'est Mme Dubois. Je voudrais voir le docteur mardi prochain le matin "
    "pour un renouvellement d'ordonnance.",
    "Salut, je viens d'emménager à Lille et je cherche un médecin traitant. "
    "Je m'appelle Karim Benali, je suis dispo demain après-midi.",
    "Il me faudrait un rdv pour mon fils qui tousse.",
]


# --- 3. Nettoyage et validation ---------------------------------------------
def nettoyer(texte):
    """Retire les éventuelles balises ```json ... ``` que certains modèles ajoutent
    malgré la consigne."""
    texte = texte.strip()
    if texte.startswith("```"):
        # On supprime la première ligne (```json) ...
        texte = texte.split("\n", 1)[1] if "\n" in texte else ""
        # ... et tout ce qui suit le dernier ```
        texte = texte.rsplit("```", 1)[0]
    return texte.strip()


def extraire(message_patient):
    """Extrait une DemandeRDV du message, en laissant le modèle se corriger si besoin.

    Renvoie un objet DemandeRDV, ou None si le modèle échoue après plusieurs essais.
    """
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": message_patient},
    ]

    # range(MAX_CORRECTIONS + 1) : 1 essai initial + MAX_CORRECTIONS corrections
    for essai in range(MAX_CORRECTIONS + 1):
        completion = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            max_tokens=1024,
            temperature=0,  # 0 : réponses les plus stables possibles
            reasoning_effort=REASONING_EFFORT,
        )
        brut = completion.choices[0].message.content or ""

        # Double vérification :
        #   json.loads           -> est-ce du JSON valide ?
        #   model_validate       -> les champs ont-ils les bons noms et les bons types ?
        try:
            donnees = json.loads(nettoyer(brut))
            return DemandeRDV.model_validate(donnees)
        except (json.JSONDecodeError, ValidationError) as erreur:
            print(f"  [essai {essai + 1}] réponse invalide : {type(erreur).__name__}")

            # 4. Auto-correction : on ajoute à la conversation la réponse fautive
            #    du modèle ET le message d'erreur, puis on lui demande de corriger.
            messages.append({"role": "assistant", "content": brut})
            messages.append({
                "role": "user",
                "content": f"Ta réponse n'est pas valide : {erreur}\n"
                           "Corrige-la et renvoie uniquement le JSON.",
            })

    return None  # le modèle n'a pas réussi après plusieurs corrections


# --- Programme principal -------------------------------------------------------
for message in MESSAGES_PATIENTS:
    print("=" * 70)
    print(f"PATIENT : {message}\n")

    demande = extraire(message)
    if demande is None:
        print("Échec de l'extraction.")
        continue

    # model_dump_json : on réaffiche l'objet validé au format JSON
    print(demande.model_dump_json(indent=2))

    # Les données sont maintenant de vrais objets Python, utilisables par le code :
    # demande.date_souhaitee est un objet date, pas une simple chaîne de caractères.
    if demande.date_souhaitee:
        print(f"-> Recherche d'un créneau le {demande.date_souhaitee:%d/%m/%Y}"
              f" ({demande.creneau or 'toute la journée'})")
    else:
        print("-> Date manquante : il faudra la demander au patient.")
