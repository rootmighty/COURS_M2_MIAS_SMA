# Systèmes multi-agents : de l'IA distribuée à l'IA agentique

**Master 2 MIAS** — Management de l'Intelligence Artificielle en Santé

Ce cours est entièrement pratique : on construit pas à pas un assistant d'IA, en partant
d'un simple appel à un modèle de langage jusqu'à une **équipe d'agents spécialisés**
qui coopèrent avec des outils, une mémoire, des garde-fous et une base documentaire.

Chaque étape ajoute **une seule notion**, sur le **même fil rouge**, pour voir concrètement
ce qu'elle apporte et ce qu'elle coûte.

---

## Le fil rouge : Doc'Assist

**Doc'Assist** est l'assistant de secrétariat du cabinet de médecine générale (fictif)
du **Dr Martin**, à Lille. Au fil des étapes, il apprend à :

- répondre aux patients et respecter les règles du cabinet ;
- consulter l'agenda, réserver, annuler et déplacer des rendez-vous ;
- enchaîner plusieurs actions seul ;
- se souvenir des patients ;
- résister aux demandes malveillantes et protéger les données personnelles ;
- répondre aux questions pratiques à partir des documents du cabinet ;
- consulter les données publiques de data.gouv.fr ;
- travailler en équipe avec d'autres agents.

Doc'Assist **ne donne jamais de conseil médical** : il gère un secrétariat. Ce choix permet
de se concentrer sur la technique, sans risque médical.

---

## Progression

| Étape | Dossier | Notions | Doc'Assist apprend à… |
|:---:|---|---|---|
| 00 | `00_LLM_CALL` | Appel API, paramètres, tokens, streaming, modèles « thinking », LLM sans état | répondre à un message |
| 01 | `01_PROMPTS_ET_SORTIES` | System prompt, sortie JSON validée (Pydantic), auto-correction, few-shot | connaître son rôle, structurer une demande, trier les messages |
| 02 | `02_TOOLS_MANUELS` | Hallucination, outils « faits maison » | consulter l'agenda (protocole maison) |
| 03 | `03_FUNCTION_CALLING` | Function calling natif, schémas JSON, rôle `tool`, appels parallèles | utiliser ses outils proprement |
| 04 | `04_BOUCLE_AGENT` | Boucle agent, limite d'étapes, ReAct (Pensée → Action → Observation) | enchaîner plusieurs actions seul |
| 05 | `05_MCP` | Serveur et client MCP, serveur public data.gouv.fr, multi-serveurs | brancher ses outils comme un service |
| 06 | `06_MEMOIRE` | Mémoire courte (complète, fenêtre, résumé), mémoire longue, RGPD | se souvenir d'un patient |
| 07 | `07_GUARDRAILS` | Attaques, injection indirecte, protections entrée / outils / sortie, validation humaine | résister et protéger les données |
| 08 | `08_RAG_AGENTIQUE` | Embeddings, FAISS, RAG classique, RAG agentique | répondre à partir des documents du cabinet |
| 09 | `09_CREWAI_SMA` | CrewAI : agents, tâches, équipes séquentielle et hiérarchique, MCP, hooks | travailler en équipe d'agents |

Chaque dossier contient des scripts numérotés, à lancer dans l'ordre, et un `README.md`.
L'en-tête de chaque script indique comment le lancer et propose des **exercices**.

**Principe pédagogique** : on code d'abord à la main (outils, boucle agent, garde-fous…),
puis on découvre à l'étape 09 qu'un framework comme CrewAI automatise exactement ces mécanismes.
Comprendre ce qui se passe dessous permet ensuite de déboguer n'importe quel framework.

---

## Prérequis

- Bases de Python (fonctions, dictionnaires, listes, fichiers JSON)
- Notions de systèmes multi-agents classiques (agents, environnement, coordination)
- Un ordinateur portable personnel, avec un terminal et un éditeur (VS Code conseillé)
- Une connexion Internet

---

## Installation

### 1. Placer le projet hors d'un dossier synchronisé

⚠️ **Ne placez pas le projet dans un dossier synchronisé** (iCloud Drive : `Documents`, `Bureau` ;
OneDrive sous Windows). Les environnements Python contiennent des milliers de petits fichiers :
leur synchronisation peut rendre chaque lancement de script très lent (plusieurs dizaines de secondes).

Exemple : `~/Projets/cours-sma`.

### 2. Installer uv

[uv](https://docs.astral.sh/uv/) gère les versions de Python et les environnements.

macOS et Linux :

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Windows (PowerShell) :

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Fermez puis rouvrez le terminal, puis vérifiez : `uv --version`.

### 3. Créer l'environnement principal (étapes 00 à 08)

À la racine du projet :

```bash
uv venv .venv --python 3.13
source .venv/bin/activate          # Windows : .venv\Scripts\activate
uv pip install -r requirements.txt
```

Contenu de `requirements.txt` :

```
requests
python-dotenv
openai
pydantic>=2
mcp>=2
faiss-cpu
numpy
```

### 4. Créer l'environnement CrewAI (étape 09)

CrewAI nécessite **Python 3.13 au maximum** et la **version 1 du SDK MCP**, alors que l'étape 05
utilise la version 2. L'étape 09 a donc **son propre environnement** :

```bash
deactivate
uv venv .venv-crewai --python 3.13
source .venv-crewai/bin/activate   # Windows : .venv-crewai\Scripts\activate
uv pip install -r 09_CREWAI_SMA/requirements-crewai.txt
```

Pour changer d'environnement : `deactivate`, puis activez l'autre.

### 5. Configurer la clé API

```bash
cp .env.example .env
```

Puis renseignez votre clé dans `.env` (voir ci-dessous). **Ne commitez jamais le fichier `.env`.**

### 6. Vérifier l'installation

```bash
source .venv/bin/activate
python 00_LLM_CALL/01_premier_appel.py
```

Pour l'étape 09, lancez une première fois `python 09_CREWAI_SMA/01_premier_agent.py` **avant la séance** :
le premier chargement de CrewAI est long.

---

## L'API NVIDIA

Le cours utilise les modèles gratuits du catalogue NVIDIA ([build.nvidia.com](https://build.nvidia.com)),
accessibles par une API compatible OpenAI.

1. Créez un compte sur build.nvidia.com.
2. Générez une clé API (elle commence par `nvapi-`).
3. Copiez-la dans votre fichier `.env`.

**Chaque étudiant utilise sa propre clé** : les limites de requêtes sont fixées par clé,
et une clé partagée par toute la classe déclencherait des erreurs 429.

### Variables du fichier `.env`

| Variable | Rôle | Exemple |
|---|---|---|
| `NVIDIA_API_KEY` | Votre clé personnelle | `nvapi-...` |
| `NVIDIA_MODEL` | Modèle utilisé par **tous** les scripts | `nvidia/nemotron-3.5-super-vl-120b-a12b` |
| `NVIDIA_REASONING_EFFORT` | Effort de raisonnement : `low`, `medium`, `high` | `low` |
| `NVIDIA_THINKING_MODEL` | Optionnel : démo `01b` (étape 00) et manager (étape 09) | |
| `NVIDIA_EMBEDDING_MODEL` | Optionnel : modèle d'embedding (étapes 08 et 09) | `nvidia/nemotron-3.5-embed-1b` |

Les modèles récents **raisonnent avant de répondre** : ce raisonnement consomme des tokens et du temps.
`NVIDIA_REASONING_EFFORT=low` le limite fortement (voir `00_LLM_CALL/01b_modele_thinking.py`).

Le catalogue gratuit évolue : un modèle peut être retiré du jour au lendemain (erreur 410).
**Testez vos modèles quelques jours avant chaque séance.**

### Erreurs fréquentes

| Erreur | Signification | Que faire |
|---|---|---|
| 401 | Clé invalide ou absente | Vérifier `NVIDIA_API_KEY` dans `.env` |
| 404 / 410 | Modèle inconnu ou retiré du catalogue | Choisir un autre modèle sur build.nvidia.com |
| 429 | Trop de requêtes | Attendre ; les scripts réessaient automatiquement |
| 503 | Service surchargé | Réessayer plus tard ; les scripts réessaient automatiquement |
| Délai dépassé | L'API ne répond pas | Réessayer ; vérifier la connexion |
| `content` vide | Le raisonnement a consommé tous les tokens | Augmenter `max_tokens` ou baisser l'effort de raisonnement |

---

## Fichiers générés

Certains scripts créent des fichiers pendant le cours. Ils sont ignorés par Git (`.gitignore`) :

| Fichier | Créé par | Rôle |
|---|---|---|
| `agenda.json` | étapes 02 à 09 | Agenda fictif du cabinet (14 jours ouvrés, régénéré chaque jour) |
| `memoire_patients.json` | étape 06 | Mémoire longue des patients |
| `index_faiss/` | étapes 08 et 09 | Index des documents du cabinet |

Pour remettre l'agenda à zéro : `python <dossier>/outils_cabinet.py --reset`.

---

## Données et éthique

- **Toutes les données sont fictives** : cabinet, patients, agenda, documents.
  N'utilisez **jamais** de données de patients réels, ni dans le cours ni dans le mini-projet.
- Les messages envoyés à l'API partent chez un fournisseur externe, **non certifié HDS**
  (hébergement de données de santé).
- La mémoire d'un agent est une **donnée personnelle** : minimisation, pas de données médicales
  inutiles, droit à l'effacement (étape 06).
- Tout ce qui se trouve dans le contexte d'un modèle peut ressortir : vers l'utilisateur,
  vers les outils, vers le fournisseur (étape 07).
- La télémétrie de CrewAI est désactivée dans `09_CREWAI_SMA/config_llm.py`.

---

## Mini-projet

Par groupe, construire un système multi-agents avec **CrewAI**, puis le présenter avec une **démonstration en direct**.

### Choix du sujet

Choisissez un sujet dans la liste, ou proposez le vôtre (à faire valider). Le plus simple est
de reprendre le squelette de Doc'Assist sur un autre établissement :

- **Pharmacie** : disponibilité des produits, horaires de garde, préparation des commandes
- **Laboratoire d'analyses** : prise de rendez-vous, consignes de préparation, délais de résultats
- **Centre de vaccination** : créneaux, éligibilité selon des règles fictives, documents à apporter
- **Service des admissions d'un hôpital** : pré-admission, documents, orientation vers les services
- **Veille documentaire** : recherche, résumé et critique de documents sur un thème de santé publique
- **Exploration de données publiques** : répondre à des questions à partir des données de data.gouv.fr

### Cahier des charges

- Une équipe CrewAI d'**au moins 3 agents** aux rôles distincts
- **Au moins un outil** développé par le groupe, ou un **serveur MCP**
- Une **recherche documentaire (RAG)** avec FAISS, sur un corpus constitué par le groupe
- **Au moins un garde-fou** et une **validation humaine** pour les actions sensibles
- Des **données exclusivement fictives**
- Une **démonstration en direct** lors de la présentation

### La présentation

- Le cas d'usage et l'architecture de l'équipe (qui fait quoi, quels outils)
- La démonstration
- Les limites constatées : erreurs, coûts en tokens, risques, et les protections mises en place

---

## Dépannage

**Les scripts mettent longtemps à démarrer, sans rien afficher.**
Mesurez : `time python -c "import crewai"`. Si le temps total est très supérieur au temps de calcul
(`user`), le disque est lent : le projet est probablement dans un dossier synchronisé (iCloud, OneDrive).
Recréez les environnements hors de ce dossier.

**`pip` refuse d'installer CrewAI.**
Vérifiez la version de Python de l'environnement : CrewAI nécessite Python 3.13 au maximum.

**Conflit sur le paquet `mcp`.**
Les étapes 00 à 08 utilisent `mcp>=2`, l'étape 09 la version 1 imposée par CrewAI :
utilisez deux environnements séparés.

**Le serveur data.gouv.fr ne répond pas.**
C'est un service expérimental, parfois indisponible. Les scripts concernés continuent sans lui.

**L'assistant utilise un autre modèle que prévu.**
Vérifiez la valeur lue : `python -c "from dotenv import load_dotenv; import os; load_dotenv(); print(os.getenv('NVIDIA_MODEL'))"`.
