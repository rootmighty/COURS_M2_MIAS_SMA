# 09 — Système multi-agents avec CrewAI

Toutes les briques sont prêtes : appel au LLM, sorties structurées, outils, boucle agent,
mémoire, garde-fous, RAG. On les assemble maintenant dans une **équipe d'agents spécialisés**
avec le framework **CrewAI**.

## Objectifs

- Découvrir les briques de CrewAI : **Agent**, **Task**, **Crew**
- Retrouver dans le framework ce qui a été codé à la main (boucle agent, outils, garde-fous)
- Construire une équipe **séquentielle** de quatre agents avec des sorties structurées
- Garder l'**humain dans la boucle** pour les actions sur l'agenda
- Comparer avec une équipe **hiérarchique**, où un manager répartit le travail
- Réunir toutes les briques dans un **chat complet** avec le patient :
  manager, serveurs **MCP** (agenda local et data.gouv.fr), **RAG**, mémoire courte, garde-fous

## Installation : un environnement séparé

CrewAI ne fonctionne pas encore avec Python 3.14, et il dépend de la version 1 du SDK MCP,
alors que l'étape 05 utilise la version 2. Cette étape a donc **son propre environnement**,
en Python 3.13, créé avec **uv**.

### 1. Installer uv

uv est un gestionnaire de paquets et de versions de Python. Il télécharge lui-même
Python 3.13 si cette version n'est pas installée sur la machine.

macOS et Linux :

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Windows (PowerShell) :

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Autres possibilités : `brew install uv` (macOS avec Homebrew) ou `pip install uv`.

Fermez puis rouvrez le terminal, et vérifiez l'installation :

```bash
uv --version
```

### 2. Créer l'environnement de l'étape

À la racine du projet :

```bash
uv venv .venv-crewai --python 3.13
```

Activation, macOS et Linux :

```bash
source .venv-crewai/bin/activate
```

Activation, Windows (PowerShell) :

```powershell
.venv-crewai\Scripts\activate
```

### 3. Installer les dépendances

```bash
uv pip install -r 09_CREWAI_SMA/requirements-crewai.txt
```

Pour revenir à l'environnement des autres étapes : `deactivate`, puis activez `.venv`.

Le fichier `.env` à la racine du projet est utilisé tel quel. Variables utiles :

| Variable | Rôle |
|---|---|
| `NVIDIA_API_KEY` | Clé de l'API NVIDIA |
| `NVIDIA_MODEL` | Modèle des agents spécialisés |
| `NVIDIA_THINKING_MODEL` | Modèle du manager (processus hiérarchique), optionnel |
| `NVIDIA_REASONING_EFFORT` | Effort de raisonnement des agents (`low` conseillé) |
| `NVIDIA_EMBEDDING_MODEL` | Modèle d'embedding pour la recherche documentaire |

## Fichiers

| Fichier | Rôle |
|---|---|
| `config_llm.py` | Les modèles des agents et du manager (API NVIDIA via le connecteur OpenAI de CrewAI) |
| `outils_crew.py` | Les outils au format CrewAI (agenda + recherche documentaire) |
| `serveur_agenda_mcp.py` | Le serveur MCP de l'agenda (SDK MCP v1, celui de l'environnement CrewAI) |
| `garde_fous.py` | Urgence, masquage des données personnelles, contrôle de la réponse finale |
| `outils_cabinet.py`, `rag.py`, `documents/` | L'agenda, le RAG FAISS et les documents du cabinet |
| `01_premier_agent.py` | Un agent, une tâche, une équipe |
| `02_agent_avec_outils.py` | Un agent avec les outils : CrewAI gère la boucle |
| `03_equipe_sequentielle.py` | Quatre agents spécialisés, sorties Pydantic, garde-fou, validation humaine |
| `04_equipe_hierarchique.py` | Un manager délègue aux spécialistes utiles (messages fixes) |
| `05_doc_assist_complet.py` | Chat complet : manager, agenda via MCP, data.gouv.fr via MCP, RAG, mémoire, garde-fous, validation humaine |

L'index FAISS est construit automatiquement au premier usage de la recherche documentaire.
Il est préférable de le construire à l'avance, l'API d'embedding pouvant être surchargée :

## Tracing dans un UI
- créer un compte gratuit sur app.crewai.com, qui donne accès à la plateforme CrewAI AMP pour consulter les traces et les métriques ; 
crewai
- lancer `crewai login` dans le terminal ;
- passer `tracing=True` dans le Crew

```bash
python 09_CREWAI_SMA/indexer_documents.py
```

## Les serveurs MCP dans CrewAI

`05_doc_assist_complet.py` branche deux serveurs MCP :

- **l'agenda**, serveur local lancé par CrewAI (`MCPServerStdio`) ;
- **data.gouv.fr**, serveur distant (`MCPServerHTTP`), limité à 4 outils avec un filtre.

CrewAI préfixe le nom de chaque outil MCP par le nom du serveur
(ex. `python_m_serveur_agenda_mcp_reserver_creneau`).
La validation humaine utilise un **hook** `@before_tool_call`, exécuté avant chaque appel d'outil,
qu'il vienne d'un serveur MCP ou d'une fonction Python.

Si data.gouv.fr ne répond pas au démarrage, l'équipe fonctionne sans ce spécialiste.

## Ce que CrewAI fait pour nous

| Ce qu'on a codé à la main | Équivalent CrewAI |
|---|---|
| System prompt (rôle, règles) | `Agent(role=..., goal=..., backstory=...)` |
| Schémas JSON des outils | `@tool` + docstring + types |
| Boucle agent et limite d'étapes | Intégrées, avec `max_iter` |
| Sortie JSON validée par Pydantic | `Task(output_pydantic=...)` |
| Garde-fou de sortie | `Task(guardrail=...)` : l'agent recommence si le contrôle échoue |
| Retry et limite de débit | `Crew(max_rpm=...)` |
| Routeur (classification) | Processus hiérarchique : le manager choisit les spécialistes |
| Client MCP et routage vers les serveurs | `MCPServerStdio`, `MCPServerHTTP`, filtres d'outils |
| Contrôle avant chaque outil (`garde_outil`) | Hook `@before_tool_call` |

## Le manager du processus hiérarchique

Avec `manager_llm=...`, CrewAI crée lui-même le manager, avec un prompt générique en anglais
(« Crew Manager… a seasoned manager… ») qui ne connaît ni le cabinet ni l'équipe.
Avec `manager_agent=...`, on définit le manager comme n'importe quel agent : son rôle,
la composition de son équipe et ses règles de délégation.

Contraintes imposées par CrewAI :
- le manager **n'a pas d'outils** : il reçoit automatiquement les outils de délégation ;
- le manager **ne figure pas** dans la liste `agents` de l'équipe.

`04_equipe_hierarchique.py` permet de comparer les deux (variable `MANAGER_PERSONNALISE`) ;
`05_doc_assist_complet.py` utilise un manager personnalisé.

## Séquentiel ou hiérarchique ?

| | Séquentiel | Hiérarchique |
|---|---|---|
| Qui organise | Le code (ordre des tâches) | Un LLM manager |
| Tâches inutiles | Exécutées quand même | Évitées (en principe) |
| Prévisibilité | Élevée | Plus faible |
| Coût | Fixe, souvent élevé | Variable, le manager ajoute ses propres appels |
| Débogage | Simple | Plus difficile |

## À retenir

- Un framework **n'invente rien** : il automatise la boucle, les outils et les échanges
  entre agents. Comprendre ce qui se passe dessous permet de le déboguer.
- **Spécialiser** les agents réduit le nombre d'outils et la taille du prompt de chacun.
- Plus d'agents = **plus d'appels au LLM** : coût, latence et risque de 429 augmentent.
- Les décisions qui engagent (réserver, annuler) restent sous **contrôle humain**,
  exécutées par le code et non par les agents.
- Le prompt construit par CrewAI est en anglais et assez long : regardez-le en mode `verbose`.
