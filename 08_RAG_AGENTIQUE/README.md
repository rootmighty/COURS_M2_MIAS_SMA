# 08 — Le RAG agentique avec FAISS

Doc'Assist doit répondre aux questions pratiques sur le cabinet : tarifs, téléconsultation,
retards, dossier médical… Ces informations sont dans des documents. Plutôt que de tout
copier dans le prompt, on va **chercher les passages utiles** au moment de la question :
c'est le **RAG** (Retrieval-Augmented Generation).

## Objectifs

- Comprendre les **embeddings** et la **recherche sémantique** (par le sens, pas par les mots)
- **Indexer** des documents avec **FAISS**
- Construire un **RAG classique** : le code cherche, puis le LLM répond avec des sources
- Passer au **RAG agentique** : la recherche devient un **outil** que l'agent choisit d'utiliser

## Fichiers

| Fichier | Rôle |
|---|---|
| `documents/` | Les documents du cabinet (fictifs) : FAQ, tarifs, téléconsultation, absences, données personnelles |
| `rag.py` | Découpage, embeddings, index FAISS, recherche |
| `01_embeddings.py` | Comparer recherche par mots communs et recherche sémantique |
| `02_indexer_documents.py` | Découper les documents et construire l'index FAISS (à lancer une fois) |
| `03_rag_classique.py` | Recherche systématique + réponse sourcée |
| `04_rag_agentique.py` | L'agent décide quand et quoi chercher, et combine documents et agenda |
| `agent.py`, `outils_cabinet.py`, `schemas_outils.py` | La boucle agent et les outils de l'agenda |

## Installation

```bash
pip install faiss-cpu numpy
```

Ajoutez `faiss-cpu` et `numpy` dans `requirements.txt`.

Le modèle d'embedding est `nvidia/nemotron-3.5-embed-1b` (multilingue, dont le français). Pour en changer,
ajoutez `NVIDIA_EMBEDDING_MODEL=...` dans le `.env`, puis relancez l'indexation :
les vecteurs d'un modèle ne sont pas comparables à ceux d'un autre.

## Ordre d'exécution

```bash
python 08_RAG_AGENTIQUE/01_embeddings.py
python 08_RAG_AGENTIQUE/02_indexer_documents.py
python 08_RAG_AGENTIQUE/03_rag_classique.py
python 08_RAG_AGENTIQUE/04_rag_agentique.py
```

## RAG classique ou agentique ?

| | RAG classique | RAG agentique |
|---|---|---|
| Qui décide de chercher | Le code, à chaque question | L'agent, seulement si utile |
| Requête de recherche | La question telle quelle | Reformulée par l'agent, éventuellement plusieurs |
| Questions en plusieurs parties | Une seule recherche | Plusieurs recherches + autres outils |
| Coût | 1 recherche + 1 appel LLM, toujours | Variable : 1 appel si inutile, plusieurs si complexe |
| Prévisibilité | Élevée | Plus faible (dépend du modèle) |

## À retenir

- Un **embedding** représente le sens d'un texte : « Où me garer ? » trouve « parking »
  sans mot commun, là où la recherche par mots-clés échoue.
- On encode les documents en mode `passage` et les questions en mode `query`.
- Le **découpage** compte : des morceaux trop gros diluent l'information,
  trop petits perdent le contexte.
- Le RAG réduit les hallucinations **à condition** d'exiger des réponses fondées sur
  les extraits, avec des **sources**, et un « je ne sais pas » quand l'information manque.
- Les documents restent des **données lues par un outil** : un document modifié par
  un tiers peut contenir une injection indirecte.
