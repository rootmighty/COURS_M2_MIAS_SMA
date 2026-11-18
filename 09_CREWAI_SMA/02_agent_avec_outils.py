"""
02_agent_avec_outils.py
-----------------------
Un agent CrewAI équipé d'outils : agenda et recherche documentaire.

CrewAI gère lui-même la boucle agent : appel du modèle, exécution des outils,
renvoi des résultats, limite d'itérations (max_iter). C'est la boucle écrite
à la main dans les étapes précédentes, fournie par le framework.

Au premier lancement, l'index FAISS des documents est construit automatiquement.

Lancement :
    python 09_CREWAI_SMA/02_agent_avec_outils.py

EXERCICES :
    1. Dans la sortie détaillée, repérez chaque appel d'outil et son résultat.
    2. Mettez max_iter=1. Que se passe-t-il ?
    3. Retirez l'outil rechercher_documents. Comment l'agent répond-il à la question sur le tarif ?
"""

from datetime import date

from config_llm import MAX_RPM, llm_agents
from crewai import Agent, Crew, Task
from outils_crew import chercher_creneaux, lister_rdv, rechercher_documents

assistant = Agent(
    role="Assistant de secrétariat du cabinet du Dr Martin",
    goal="Répondre aux patients de façon exacte, en vérifiant chaque information avec les outils",
    backstory=(
        "Tu gères l'accueil d'un cabinet de médecine générale. Tu n'inventes jamais "
        "une disponibilité ni une information : tu vérifies dans l'agenda et dans les documents "
        "du cabinet, et tu cites tes sources. Tu ne donnes jamais de conseil médical."
    ),
    tools=[chercher_creneaux, lister_rdv, rechercher_documents],
    llm=llm_agents,
    max_iter=1,          # nombre maximum d'itérations de la boucle agent
    verbose=True,
)

reponse_patient = Task(
    description=(
        "Nous sommes le {date_du_jour}. Un patient écrit au cabinet :\n"
        "« {message} »\n"
        "Utilise les outils nécessaires, puis rédige la réponse du secrétariat."
    ),
    expected_output=(
        "Une réponse courte et chaleureuse au patient, avec les informations vérifiées "
        "et la source des informations tirées des documents entre crochets."
    ),
    agent=assistant, # Quel agent se charge de la tâche
)

equipe = Crew(
    agents=[assistant],
    tasks=[reponse_patient],
    max_rpm=MAX_RPM,
    verbose=True,
    tracing=False,
)

resultat = equipe.kickoff(inputs={
    "date_du_jour": date.today().isoformat(),
    "message": "Combien coûte une consultation, et vous avez de la place demain matin ?",
})

print("\n" + "=" * 70)
print(f"RÉPONSE FINALE :\n{resultat.raw}")
print(f"\nTokens utilisés : {resultat.token_usage.total_tokens}")
