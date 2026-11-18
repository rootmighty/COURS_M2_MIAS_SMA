# 01 — Prompts et sorties structurées

Doc'Assist sait maintenant parler. Dans cette étape, il apprend **qui il est**,
à **transformer un message en données** et à **trier les demandes**.

## Objectifs

- Comprendre le rôle du **system prompt** (identité, rôle, règles)
- Obtenir une **sortie JSON** et la **valider** avant de l'utiliser
- Laisser le modèle **se corriger** à partir d'un message d'erreur
- Classer des messages avec la technique **few-shot**

## Scripts

| Fichier | Notion |
|---|---|
| `01_system_prompt.py` | Mêmes questions avec et sans system prompt |
| `02_sortie_json.py` | Extraction d'une demande de RDV en JSON, validée par Pydantic, avec auto-correction |
| `03_classification_few_shot.py` | Routeur : rendez-vous, annulation, question pratique, urgence |

Chaque script contient des **exercices** dans son en-tête.

## À retenir

- Le modèle ne sait que ce qu'on lui dit : rôle, règles, **date du jour**…
- Une sortie de LLM est une **donnée non fiable** : on la nettoie et on la valide.
- `temperature=0` pour l'extraction et la classification : on veut de la stabilité.
- Le schéma Pydantic décrit le format attendu. On retrouvera exactement ce principe
  avec le **function calling** : les paramètres des outils sont décrits par un schéma JSON.
- Le classifieur de `03` est un premier **routeur**, l'idée de base des systèmes multi-agents.
