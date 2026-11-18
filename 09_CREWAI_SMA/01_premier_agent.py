"""
01_premier_agent.py
-------------------
Premier pas avec CrewAI : un agent, une tâche, une équipe.

Les trois briques de CrewAI :
    - Agent : un rôle, un objectif, un contexte (backstory) et un modèle
    - Task  : ce qu'il faut faire (description) et ce qu'on attend (expected_output)
    - Crew  : l'équipe qui exécute les tâches avec ses agents

Les variables entre accolades ({message}, {date_du_jour}) sont remplacées
par les valeurs passées à kickoff(inputs=...).

Lancement :
    python 09_CREWAI_SMA/01_premier_agent.py

EXERCICES :
    1. Observez la sortie détaillée (verbose) : retrouvez le rôle, l'objectif et la tâche.
       À quoi ressemble le prompt construit par CrewAI ?
    2. Modifiez le backstory (ex. "secrétaire très formelle"). La réponse change-t-elle ?
    3. Où se trouve le system prompt que nous écrivions à la main jusqu'ici ?
"""

from datetime import date

from config_llm import MAX_RPM, llm_agents
from crewai import Agent, Crew, Task

# --- L'agent ------------------------------------------------------------------
secretaire = Agent(
    role="Secrétaire médicale du cabinet du Dr Martin",
    goal="Accueillir les patients avec chaleur et répondre à leurs demandes pratiques",
    backstory=(
        "Tu travailles depuis dix ans au secrétariat d'un cabinet de médecine générale à Lille. "
        "Le cabinet est ouvert du lundi au vendredi, de 9h à 12h et de 14h à 18h. "
        "Tu vouvoies les patients et tu ne donnes jamais de conseil médical."
    ),
    llm=llm_agents,
    verbose=True,
)

# --- La tâche -------------------------------------------------------------------
reponse_patient = Task(
    description=(
        "Nous sommes le {date_du_jour}. Un patient écrit au cabinet :\n"
        "« {message} »\n"
        "Rédige la réponse du secrétariat."
    ),
    expected_output="Une réponse courte (3 phrases maximum), chaleureuse, adressée au patient.",
    agent=secretaire,  # Quel agent se charge de la tâche
)

# --- L'équipe ---------------------------------------------------------------------
equipe = Crew(
    agents=[secretaire],
    tasks=[reponse_patient],
    max_rpm=MAX_RPM,
    verbose=True,
    tracing=False,
)

resultat = equipe.kickoff(inputs={
    "date_du_jour": date.today().isoformat(),
    "message": "Bonjour, vous êtes ouverts le samedi matin ?",
})

print("\n" + "=" * 70)
print(f"RÉPONSE FINALE :\n{resultat.raw}")
print(f"\nTokens utilisés : {resultat.token_usage.total_tokens}")
