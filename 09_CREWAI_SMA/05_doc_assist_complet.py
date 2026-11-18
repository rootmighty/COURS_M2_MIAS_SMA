"""
05_doc_assist_complet.py
------------------------
Doc'Assist complet : une équipe hiérarchique d'agents, en conversation avec le patient.

Toutes les briques du cours sont réunies :
    - un manager (LLM) qui répartit le travail entre les spécialistes ;
    - les outils de l'agenda, servis par un serveur MCP local (serveur_agenda_mcp.py) ;
    - les données publiques de data.gouv.fr, via leur serveur MCP distant ;
    - la recherche documentaire (RAG FAISS) dans les documents du cabinet ;
    - une mémoire courte : les derniers échanges sont transmis à chaque demande ;
    - des garde-fous : urgence et données personnelles en entrée, validation humaine
      des actions sur l'agenda, contrôle de la réponse finale.

                          ┌──> Documentaliste        (documents du cabinet, RAG)
    message ──> Manager ──┼──> Planificateur         (agenda, serveur MCP local)
                          └──> Données publiques     (data.gouv.fr, serveur MCP distant)
                  │
                  └──> réponse finale au patient

    Le manager ne sollicite que les spécialistes utiles à la demande :
    l'un, plusieurs, ou aucun.

Le manager est défini dans le script (manager_agent) : il connaît le cabinet, son équipe
et ses règles de délégation. Il utilise llm_superviseur
(NVIDIA_THINKING_MODEL s'il est défini dans le .env).

Lancement (environnement .venv-crewai activé) :
    python 09_CREWAI_SMA/05_doc_assist_complet.py

Questions à tester :
    Vous : Bonjour, je suis Mme Dubois. Combien coûte une consultation ?
    Vous : Vous avez de la place demain matin ?
    Vous : Je prends le premier créneau.
    Vous : Existe-t-il des données publiques sur les pharmacies en France ?
    Vous : J'ai une douleur dans la poitrine.

EXERCICES :
    1. Pour chaque message, quels spécialistes le manager a-t-il sollicités ?
    2. Refusez une réservation lors de la validation. Comment l'équipe réagit-elle ?
    3. Comparez les tokens d'une question simple et d'une question en plusieurs parties.
    4. Retirez l'historique de la description de la tâche. "Je prends le premier créneau"
       fonctionne-t-il encore ?
    5. Quels sont les avantages et les risques de laisser un LLM organiser le travail ?
"""

import os
import shutil
import sys
from datetime import date
from pathlib import Path

from config_llm import MAX_RPM, llm_agents, llm_superviseur
from crewai import Agent, Crew, Process, Task
from crewai.hooks import before_tool_call
from crewai.mcp import MCPServerHTTP, MCPServerStdio, create_static_tool_filter

from garde_fous import detecter_urgence, masquer_donnees_personnelles, verifier_reponse
from outils_crew import rechercher_documents

DOSSIER = Path(__file__).parent
URL_DATAGOUV = "https://mcp.data.gouv.fr/mcp"
TOURS_EN_MEMOIRE = 4   # nombre d'échanges précédents transmis à l'équipe

# Outils de l'agenda qui modifient les rendez-vous : validation humaine obligatoire
ACTIONS_SENSIBLES = ["reserver_creneau", "annuler_rdv", "deplacer_rdv"]


# =============================================================================
# SERVEURS MCP
# =============================================================================

# --- Serveur MCP local de l'agenda --------------------------------------------------
# Lancé avec "python -m serveur_agenda_mcp" : CrewAI construit le nom des outils à partir
# de la commande, une commande courte donne donc des noms lisibles
# (ex. python_m_serveur_agenda_mcp_chercher_creneaux).
# PATH commence par le dossier de l'interpréteur en cours : "python" désigne celui du .venv-crewai.
SERVEUR_AGENDA = MCPServerStdio(
    command="python",
    args=["-m", "serveur_agenda_mcp"],
    env={
        **os.environ,
        "PATH": f"{Path(sys.executable).parent}{os.pathsep}{os.environ.get('PATH', '')}",
        "PYTHONPATH": str(DOSSIER),
    },
)

# --- Serveur MCP distant de data.gouv.fr -----------------------------------------------
# Seuls les outils utiles sont conservés : moins d'outils = prompt plus court, choix plus simple
SERVEUR_DATAGOUV = MCPServerHTTP(
    url=URL_DATAGOUV,
    tool_filter=create_static_tool_filter(
        allowed_tool_names=["search_datasets", "get_dataset_info",
                            "list_dataset_resources", "query_resource_data"],
    ),
)


def message_erreur(erreur):
    """Renvoie le message de la première erreur réelle (les erreurs réseau
    arrivent parfois regroupées dans un ExceptionGroup)."""
    while isinstance(erreur, BaseExceptionGroup) and erreur.exceptions:
        erreur = erreur.exceptions[0]
    return f"{type(erreur).__name__} : {erreur}"


def charger_outils_mcp(agent, serveur, nom, essais=2):
    """Charge les outils d'un serveur MCP pour un agent. Renvoie True en cas de succès.

    En processus hiérarchique, un agent sollicité par délégation ne charge pas
    lui-même ses serveurs MCP (paramètre mcps=) : on lui fournit donc directement les outils.
    """
    for essai in range(1, essais + 1):
        try:
            agent.tools = agent.get_mcp_tools([serveur])
            print(f"✅ Serveur {nom} : {[o.name for o in agent.tools]}")
            return True
        except Exception as erreur:
            print(f"⚠️  Serveur {nom} indisponible (essai {essai}/{essais}) : {message_erreur(erreur)}")
    return False


# =============================================================================
# VALIDATION HUMAINE DES ACTIONS SUR L'AGENDA
# =============================================================================

@before_tool_call
def valider_action_sensible(contexte):
    """Hook CrewAI exécuté avant chaque appel d'outil.

    Renvoie None pour laisser passer l'appel, False pour le bloquer.
    Les noms des outils MCP sont préfixés par le nom du serveur : on compare la fin du nom.
    """
    if not any(contexte.tool_name.endswith(action) for action in ACTIONS_SENSIBLES):
        return None
    print(f"\n   🙋 Validation requise : {contexte.tool_name}({contexte.tool_input})")
    reponse = input("      Le patient confirme-t-il cette action ? (o/n) : ").strip().lower()
    if reponse in {"o", "oui", "y", "yes"}:
        return None
    print("      Action refusée.")
    return False


# =============================================================================
# LES SPÉCIALISTES
# =============================================================================
# allow_delegation=False : seul le manager distribue le travail

documentaliste = Agent(
    role="Documentaliste du cabinet",
    goal="Trouver dans les documents du cabinet la réponse exacte aux questions pratiques",
    backstory="Tu connais tous les documents du cabinet (tarifs, téléconsultation, absences, "
              "règles d'annulation...). Tu cites toujours tes sources et tu n'inventes jamais "
              "une information absente des documents.",
    tools=[rechercher_documents],
    llm=llm_agents,
    allow_delegation=False,
    max_iter=4,
    verbose=True,
)

planificateur = Agent(
    role="Planificateur des rendez-vous",
    goal="Consulter l'agenda et gérer les rendez-vous selon les demandes du patient",
    backstory="Tu gères l'agenda du cabinet. Tu ne réserves, n'annules ou ne déplaces un "
              "rendez-vous que si le patient l'a explicitement demandé et que tu connais son nom. "
              "Chaque action est soumise à la validation du patient.",
    llm=llm_agents,
    allow_delegation=False,
    max_iter=5,
    verbose=True,
)

donnees_publiques = Agent(
    role="Chargé des données publiques",
    goal="Trouver des jeux de données publiques pertinents sur data.gouv.fr",
    backstory="Tu explores le catalogue de data.gouv.fr avec des recherches par mots-clés "
              "courts. Après 2 ou 3 recherches, tu réponds avec ce que tu as trouvé, "
              "en citant les jeux de données et leur lien.",
    llm=llm_agents,
    allow_delegation=False,
    max_iter=4,
    verbose=True,
)


# =============================================================================
# L'ÉQUIPE
# =============================================================================

# =============================================================================
# LE MANAGER
# =============================================================================

def creer_manager(avec_datagouv):
    """Crée le manager de l'équipe. Sa description de l'équipe dépend des spécialistes disponibles.

    Règles imposées par CrewAI : le manager n'a pas d'outils (il reçoit automatiquement
    les outils de délégation) et il ne figure pas dans la liste agents de l'équipe.
    """
    equipe = [
        "- le documentaliste, pour les questions pratiques sur le cabinet "
        "(tarifs, téléconsultation, absences, règles d'annulation, données personnelles) ;",
        "- le planificateur, pour les disponibilités et les rendez-vous "
        "(consulter, réserver, annuler, déplacer) ;",
    ]
    if avec_datagouv:
        equipe.append("- le chargé des données publiques, pour les jeux de données de data.gouv.fr ;")

    return Agent(
        role="Responsable du secrétariat du cabinet du Dr Martin",
        goal="Répondre à chaque patient de façon exacte et rapide, "
             "en ne sollicitant que les spécialistes utiles",
        backstory="\n".join([
            "Tu coordonnes l'équipe du secrétariat d'un cabinet de médecine générale à Lille.",
            "Ton équipe :",
            *equipe,
            "Règles :",
            "- Pour une simple salutation ou une question à laquelle tu peux répondre seul, ne délègue pas.",
            "- Ne délègue à un spécialiste que ce qui relève de son domaine, avec une consigne précise "
            "qui reprend les informations utiles de la conversation (nom du patient, date souhaitée...).",
            "- Ne demande une réservation, une annulation ou un déplacement que si le patient l'a "
            "explicitement demandé.",
            "- Vérifie que les réponses des spécialistes répondent bien à la demande avant de rédiger.",
            "- Ne donne jamais de conseil médical ; en cas d'urgence, demande d'appeler le 15.",
            "- Rédige la réponse finale en français, en vouvoyant le patient.",
        ]),
        llm=llm_superviseur,
        verbose=True,
    )


def creer_equipe():
    """Crée l'équipe hiérarchique (sans le spécialiste data.gouv.fr s'il est indisponible)."""
    if not charger_outils_mcp(planificateur, SERVEUR_AGENDA, "agenda"):
        raise SystemExit("Le serveur MCP de l'agenda est indispensable : arrêt.")
    specialistes = [documentaliste, planificateur]

    avec_datagouv = charger_outils_mcp(donnees_publiques, SERVEUR_DATAGOUV, "data.gouv.fr")
    if avec_datagouv:
        specialistes.append(donnees_publiques)
    else:
        print("   L'équipe fonctionnera sans le chargé des données publiques.")

    traitement = Task(
        description=(
            "Nous sommes le {date_du_jour}. Tu réponds au nom du secrétariat du cabinet du Dr Martin.\n\n"
            "Échanges précédents avec le patient :\n{historique}\n\n"
            "Nouveau message du patient :\n« {message} »\n\n"
            "Fais traiter cette demande par les spécialistes utiles, et seulement eux, puis rédige "
            "la réponse au patient. Aucun conseil médical. Cite les sources des documents du cabinet "
            "et des données publiques."
        ),
        expected_output="La réponse au patient, chaleureuse et concise, avec ses sources entre crochets.",
        guardrail=verifier_reponse,
        guardrail_max_retries=2,
    )

    return Crew(
        agents=specialistes,
        tasks=[traitement],
        process=Process.hierarchical,   # un manager organise le travail
        manager_agent=creer_manager(avec_datagouv),
        max_rpm=MAX_RPM,
        verbose=True,
        tracing=False,
    )


def formater_historique(historique):
    """Met en forme les derniers échanges pour la description de la tâche."""
    if not historique:
        return "(début de la conversation)"
    return "\n".join(f"Patient : {q}\nSecrétariat : {r}" for q, r in historique[-TOURS_EN_MEMOIRE:])


# =============================================================================
# PROGRAMME PRINCIPAL : LE CHAT
# =============================================================================

def main():
    print("Connexion aux serveurs MCP...")
    equipe = creer_equipe()

    print("\nDoc'Assist (équipe hiérarchique) — tapez 'exit' pour quitter.\n")
    historique = []        # liste de (message du patient, réponse)
    total_precedent = 0    # le compteur de tokens de l'équipe s'additionne d'un kickoff à l'autre

    while True:
        try:
            message = input("Vous : ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if message.lower() in {"exit", "quit"}:
            break
        if not message:
            continue

        # --- Garde-fous d'entrée ---
        urgence = detecter_urgence(message)
        if urgence:
            print(f"Doc'Assist : {urgence}\n")
            continue
        message, trouvees = masquer_donnees_personnelles(message)
        if trouvees:
            print(f"   🛡️  Données masquées avant envoi : {trouvees}")

        # --- Travail de l'équipe ---
        try:
            resultat = equipe.kickoff(inputs={
                "date_du_jour": date.today().isoformat(),
                "historique": formater_historique(historique),
                "message": message,
            })
            reponse = resultat.raw
            tokens = resultat.token_usage.total_tokens - total_precedent
            total_precedent = resultat.token_usage.total_tokens
        except Exception as erreur:
            # Échec du garde-fou de sortie ou erreur technique : pas de réponse automatique
            print(f"\n   ⚠️  Échec de l'équipe : {erreur}")
            reponse = "Je transmets votre demande au secrétariat, qui vous recontactera."
            tokens = 0

        historique.append((message, reponse))
        print("\n" + "=" * 70)
        print(f"Doc'Assist : {reponse}")
        print(f"   📊 {tokens} tokens pour ce message\n")


if __name__ == "__main__":
    main()
