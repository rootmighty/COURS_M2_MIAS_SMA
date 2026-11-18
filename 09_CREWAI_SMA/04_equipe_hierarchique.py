"""
04_equipe_hierarchique.py
-------------------------
Un système multi-agents hiérarchique : un manager répartit le travail.

Dans le processus séquentiel, toutes les tâches sont exécutées, même inutiles.
Ici, un agent manager (créé par CrewAI) reçoit la demande, décide quels spécialistes
solliciter, leur délègue du travail, vérifie leurs réponses et produit la réponse finale.

                          ┌──> Documentaliste (si question pratique)
    message ──> Manager ──┤
                          └──> Planificateur  (si demande de rendez-vous)
                  │
                  └──> réponse finale au patient

    Le manager ne sollicite que les spécialistes utiles à la demande :
    l'un, l'autre, les deux, ou aucun.

Deux managers possibles (variable MANAGER_PERSONNALISE) :
    False : manager créé automatiquement par CrewAI (manager_llm), avec un prompt
            générique en anglais qui ne connaît ni le cabinet ni l'équipe ;
    True  : manager défini par nous (manager_agent), avec son rôle, son équipe
            et ses règles de délégation.
Dans les deux cas, le manager utilise llm_superviseur
(NVIDIA_THINKING_MODEL s'il est défini dans le .env).

Lancement :
    python 09_CREWAI_SMA/04_equipe_hierarchique.py

EXERCICES :
    1. Pour chaque message, quels spécialistes le manager a-t-il sollicités ?
    2. Comparez les tokens avec le processus séquentiel. Lequel coûte le plus ? Pourquoi ?
    3. Le manager a-t-il parfois délégué une tâche au mauvais spécialiste ?
    4. Ajoutez un message "Bonjour !". Le manager sollicite-t-il quelqu'un ?
    5. Passez MANAGER_PERSONNALISE à False, puis à True. Comparez les délégations
       et les tokens, en particulier sur "Bonjour !".
"""

from datetime import date

from config_llm import MAX_RPM, llm_agents, llm_superviseur
from crewai import Agent, Crew, Process, Task
from outils_crew import chercher_creneaux, lister_rdv, rechercher_documents

MANAGER_PERSONNALISE = True

MESSAGES = [
    "Bonjour",
    "Je ne suis pas venu depuis deux ans, je peux faire une téléconsultation ?",
    "Bonjour, c'est M. Leroy. Vous avez de la place jeudi après-midi ?",
    "Combien coûte une visite à domicile, et quel jour le docteur se déplace-t-il ?",
]

# --- Les spécialistes -----------------------------------------------------------
# allow_delegation=False : seul le manager distribue le travail
documentaliste = Agent(
    role="Documentaliste du cabinet",
    goal="Trouver dans les documents du cabinet la réponse exacte aux questions pratiques",
    backstory="Tu connais tous les documents du cabinet. Tu cites toujours tes sources et "
              "tu n'inventes jamais une information absente des documents.",
    tools=[rechercher_documents],
    llm=llm_agents,
    allow_delegation=False,
    max_iter=4,
    verbose=True,
)

planificateur = Agent(
    role="Planificateur des rendez-vous",
    goal="Trouver des créneaux libres adaptés aux souhaits du patient",
    backstory="Tu gères l'agenda du cabinet. Tu proposes des créneaux mais tu ne réserves jamais.",
    tools=[chercher_creneaux, lister_rdv],
    llm=llm_agents,
    allow_delegation=False,
    max_iter=4,
    verbose=True,
)

# --- Le manager personnalisé ------------------------------------------------------------
# Règles imposées par CrewAI : le manager n'a pas d'outils (il reçoit automatiquement
# les outils de délégation) et il ne figure pas dans la liste agents de l'équipe.
manager = Agent(
    role="Responsable du secrétariat du cabinet du Dr Martin",
    goal="Répondre à chaque patient de façon exacte et rapide, "
         "en ne sollicitant que les spécialistes utiles",
    backstory="""Tu coordonnes l'équipe du secrétariat d'un cabinet de médecine générale.
Ton équipe :
- le documentaliste, pour les questions pratiques (tarifs, téléconsultation, absences, règles) ;
- le planificateur, pour les disponibilités et les rendez-vous.
Règles :
- Pour une simple salutation ou une question à laquelle tu peux répondre seul, ne délègue pas.
- Ne délègue à un spécialiste que ce qui relève de son domaine, avec une consigne précise.
- Vérifie que les réponses des spécialistes répondent bien à la demande avant de rédiger.
- Ne donne jamais de conseil médical ; en cas d'urgence, demande d'appeler le 15.
- Rédige la réponse finale en français, en vouvoyant le patient.""",
    llm=llm_superviseur,
    verbose=True,
)

# --- La tâche globale ---------------------------------------------------------------
# Pas d'agent assigné : c'est le manager qui décide qui travaille
traitement = Task(
    description=(
        "Nous sommes le {date_du_jour}. Un patient écrit au cabinet du Dr Martin :\n"
        "« {message} »\n"
        "Fais traiter cette demande par les spécialistes utiles, et seulement eux, "
        "puis rédige la réponse finale au patient. Aucun conseil médical ; en cas d'urgence, "
        "demander d'appeler le 15."
    ),
    expected_output="La réponse au patient, chaleureuse, 6 phrases maximum, avec les sources entre crochets.",
)

# Manager personnalisé (manager_agent) ou manager automatique de CrewAI (manager_llm)
if MANAGER_PERSONNALISE:
    parametres_manager = {"manager_agent": manager}
else:
    parametres_manager = {"manager_llm": llm_superviseur}

equipe = Crew(
    agents=[documentaliste, planificateur],   # le manager ne fait pas partie de cette liste
    tasks=[traitement],
    process=Process.hierarchical,             # un manager organise le travail
    **parametres_manager,
    max_rpm=MAX_RPM,
    verbose=True,
    tracing=False,
)

# --- Exécution sur plusieurs messages ------------------------------------------------
print(f"Manager : {'personnalisé' if MANAGER_PERSONNALISE else 'automatique (CrewAI)'}")
bilan = []
total_precedent = 0   # le compteur de tokens de l'équipe s'additionne d'un kickoff à l'autre
for message in MESSAGES:
    print("\n" + "#" * 70)
    print(f"PATIENT : {message}")
    resultat = equipe.kickoff(inputs={"date_du_jour": date.today().isoformat(), "message": message})
    print(f"\nRÉPONSE : {resultat.raw}")
    total = resultat.token_usage.total_tokens
    bilan.append((message, total - total_precedent))
    total_precedent = total

print("\n" + "=" * 70)
for message, tokens in bilan:
    print(f"{tokens:>7} tokens | {message}")
