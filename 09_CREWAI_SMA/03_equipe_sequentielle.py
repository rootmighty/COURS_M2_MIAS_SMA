"""
03_equipe_sequentielle.py
-------------------------
Un système multi-agents : quatre agents spécialisés qui travaillent l'un après l'autre.

    message ──> [Accueil] ──┬──> [Documentaliste] ──┐
                            └──> [Planificateur] ───┴──> [Rédacteur] ──> réponse
                                                                │
                                        validation humaine <────┘ (réservation)

    Accueil        : comprend la demande et la structure (sortie Pydantic)
    Documentaliste : cherche les réponses aux questions pratiques dans les documents
    Planificateur  : propose des créneaux libres, sans rien réserver
    Rédacteur      : rédige la réponse finale (contrôlée par un garde-fou)

Chaque tâche reçoit les résultats des tâches précédentes grâce au paramètre `context`.
La réservation n'est pas confiée aux agents : elle est faite par le code,
après validation par l'humain.

Lancement :
    python 09_CREWAI_SMA/03_equipe_sequentielle.py

Messages à tester :
    - Bonjour, je suis Mme Dubois. Je voudrais un rendez-vous demain matin. Je peux payer par chèque ?
    - Je ne suis pas venu depuis deux ans, je peux faire une téléconsultation ?
    - J'ai une douleur dans la poitrine depuis ce matin.

EXERCICES :
    1. Pour le message sur la téléconsultation, le planificateur a-t-il été utile ?
       Combien d'appels au modèle ont été faits pour rien ?
    2. Ouvrez la sortie de l'accueil : à quoi sert output_pydantic ?
    3. Faites échouer le garde-fou (ex. limite de 50 caractères). Que fait CrewAI ?
    4. Comparez le nombre de tokens avec celui de 02_agent_avec_outils.py.
"""

import re
import sys
from datetime import date
from typing import Literal, Optional

from config_llm import MAX_RPM, llm_agents
from crewai import Agent, Crew, Process, Task
from pydantic import BaseModel, Field

import outils_cabinet as agenda
from outils_crew import chercher_creneaux, lister_rdv, rechercher_documents


# --- Formats de sortie structurés ------------------------------------------------
class DemandePatient(BaseModel):
    """Informations extraites du message du patient par l'agent d'accueil."""
    nom: Optional[str] = Field(None, description="Nom du patient, null si absent")
    veut_rendez_vous: bool = Field(description="true si le patient demande un rendez-vous")
    date_souhaitee: Optional[str] = Field(None, description="Date souhaitée AAAA-MM-JJ, null si absente")
    moment: Optional[Literal["matin", "apres-midi"]] = Field(None, description="Moment souhaité")
    question_pratique: Optional[str] = Field(None, description="Question sur le fonctionnement du cabinet")
    urgence: bool = Field(description="true si le message décrit un signe d'urgence médicale")


class PropositionCreneaux(BaseModel):
    """Créneaux proposés par le planificateur."""
    date: Optional[str] = Field(None, description="Date des créneaux proposés, AAAA-MM-JJ")
    creneaux: list[str] = Field(default_factory=list, description="Heures proposées (HH:MM), 3 au maximum")


# --- Garde-fou sur la réponse finale ----------------------------------------------
MOTS_INTERDITS = ["paracétamol", "ibuprofène", "doliprane", "antibiotique", "posologie", "diagnostic"]
MAX_PHRASES = 6
MAX_CARACTERES = 1500


def compter_phrases(texte):
    """Compte les phrases : morceaux de texte terminés par un point, ! ou ?."""
    texte = re.sub(r"\[[^\]]*\]", "", texte)   # les sources entre crochets ne comptent pas
    return len([p for p in re.split(r"[.!?]+(?:\s|$)", texte) if p.strip()])


def verifier_reponse(sortie):
    """Garde-fou CrewAI : renvoie (True, sortie) si la réponse est acceptable,
    sinon (False, message d'erreur) et CrewAI demande à l'agent de recommencer.

    Le message d'erreur doit décrire précisément le problème mesuré :
    c'est la seule indication dont l'agent dispose pour corriger sa réponse.
    """
    texte = sortie.raw
    print(f"   🛡️  Garde-fou : {compter_phrases(texte)} phrases, {len(texte)} caractères "
          f"— début : {texte[:80]!r}")
    interdits = [mot for mot in MOTS_INTERDITS if mot in texte.lower()]
    if interdits:
        return False, (f"La réponse contient des termes médicaux interdits : {interdits}. "
                       "Reformule sans aucun conseil médical.")
    phrases = compter_phrases(texte)
    if phrases > MAX_PHRASES:
        return False, (f"La réponse contient {phrases} phrases, le maximum est {MAX_PHRASES}. "
                       "Supprime les phrases les moins utiles.")
    if len(texte) > MAX_CARACTERES:
        return False, (f"La réponse fait {len(texte)} caractères, le maximum est {MAX_CARACTERES}. "
                       "Raccourcis les phrases et cite les sources par le seul nom du fichier, "
                       "sans le titre de la section.")
    return True, sortie


# --- Les agents --------------------------------------------------------------------
accueil = Agent(
    role="Chargé d'accueil",
    goal="Comprendre précisément la demande du patient et en extraire les informations utiles",
    backstory="Tu reçois tous les messages adressés au cabinet du Dr Martin et tu les analyses.",
    llm=llm_agents,
    verbose=True,
)

documentaliste = Agent(
    role="Documentaliste du cabinet",
    goal="Trouver dans les documents du cabinet la réponse exacte aux questions pratiques",
    backstory="Tu connais tous les documents du cabinet. Tu cites toujours tes sources et "
              "tu n'inventes jamais une information absente des documents.",
    tools=[rechercher_documents],
    llm=llm_agents,
    max_iter=4,
    verbose=True,
)

planificateur = Agent(
    role="Planificateur des rendez-vous",
    goal="Proposer des créneaux libres adaptés aux souhaits du patient",
    backstory="Tu gères l'agenda du cabinet. Tu proposes des créneaux mais tu ne réserves jamais toi-même.",
    tools=[chercher_creneaux, lister_rdv],
    llm=llm_agents,
    max_iter=4,
    verbose=True,
)

redacteur = Agent(
    role="Rédacteur des réponses aux patients",
    goal="Rédiger une réponse claire, chaleureuse et exacte à partir du travail de l'équipe",
    backstory="Tu écris au nom du secrétariat. Tu vouvoies le patient, tu ne donnes jamais "
              "de conseil médical, et en cas d'urgence tu demandes d'appeler le 15.",
    llm=llm_agents,
    verbose=True,
)

# --- Les tâches ------------------------------------------------------------------
tache_accueil = Task(
    description="Nous sommes le {date_du_jour}. Analyse ce message de patient :\n« {message} »",
    expected_output="Les informations de la demande, au format demandé.",
    output_pydantic=DemandePatient,
    agent=accueil,
)

tache_documents = Task(
    description=(
        "Si la demande contient une question pratique sur le cabinet, cherche la réponse dans "
        "les documents et résume-la avec ses sources. Sinon, réponds uniquement : "
        "« Aucune recherche nécessaire »."
    ),
    expected_output="La réponse à la question pratique avec ses sources, ou « Aucune recherche nécessaire ».",
    context=[tache_accueil],
    agent=documentaliste,
)

tache_planning = Task(
    description=(
        "Nous sommes le {date_du_jour}. Si le patient veut un rendez-vous, cherche les créneaux libres "
        "à la date souhaitée (ou au prochain jour ouvré) et propose jusqu'à 3 créneaux adaptés au moment "
        "souhaité. Ne réserve rien. Si aucun rendez-vous n'est demandé, renvoie une liste vide."
    ),
    expected_output="La date et les créneaux proposés, au format demandé.",
    output_pydantic=PropositionCreneaux,
    context=[tache_accueil],
    agent=planificateur,
)

tache_reponse = Task(
    description=(
        "Rédige la réponse finale au patient à partir de l'analyse de la demande, des informations "
        "documentaires et des créneaux proposés. Si des créneaux sont proposés, demande au patient "
        "lequel il choisit. En cas d'urgence, demande uniquement d'appeler le 15."
    ),
    expected_output="La réponse au patient, 6 phrases maximum, avec les sources entre crochets.",
    context=[tache_accueil, tache_documents, tache_planning],
    guardrail=verifier_reponse,
    guardrail_max_retries=3,      # nombre de nouvelles tentatives si le garde-fou échoue
    agent=redacteur,
)

equipe = Crew(
    agents=[accueil, documentaliste, planificateur, redacteur],
    tasks=[tache_accueil, tache_documents, tache_planning, tache_reponse],
    process=Process.sequential,   # les tâches s'exécutent dans l'ordre de la liste
    max_rpm=MAX_RPM,
    verbose=True,
    tracing=False, # Attention les donnéss sont envoyées à CrewAI pour le tracing, ne pas activer en production (RGPD, confidentialité, HDS)
)

# --- Exécution ---------------------------------------------------------------------
EXEMPLE = ("Bonjour, je suis Mme Dubois. Je voudrais un rendez-vous demain matin. "
           "Je peux payer par chèque ?")
message = input(f"Message du patient (Entrée pour l'exemple) :\n> ").strip() or EXEMPLE

try:
    resultat = equipe.kickoff(inputs={"date_du_jour": date.today().isoformat(), "message": message})
except Exception as erreur:
    # Le garde-fou a échoué à chaque tentative (ou une autre erreur est survenue) :
    # aucune réponse automatique n'est envoyée, la demande est transmise à un humain.
    print("\n" + "=" * 70)
    print(f"Échec de l'équipe : {erreur}")
    print("Aucune réponse automatique envoyée : demande transmise au secrétariat.")
    sys.exit(1)

# Résultats structurés des tâches
demande = tache_accueil.output.pydantic
proposition = tache_planning.output.pydantic

print("\n" + "=" * 70)
print(f"ANALYSE DE LA DEMANDE : {demande}")
print(f"CRÉNEAUX PROPOSÉS     : {proposition}")
print(f"\nRÉPONSE AU PATIENT :\n{resultat.raw}")
print(f"\nTokens utilisés : {resultat.token_usage.total_tokens}")

# --- Validation humaine et réservation par le code ------------------------------
if demande and proposition and proposition.creneaux and demande.nom and not demande.urgence:
    print("\n" + "=" * 70)
    for numero, heure in enumerate(proposition.creneaux, start=1):
        print(f"  {numero}. {proposition.date} à {heure}")
    choix = input("Créneau choisi par le patient (numéro, Entrée pour aucun) : ").strip()
    if choix.isdigit() and 1 <= int(choix) <= len(proposition.creneaux):
        heure = proposition.creneaux[int(choix) - 1]
        print(agenda.reserver_creneau(proposition.date, heure, demande.nom))
    else:
        print("Aucune réservation effectuée.")
