# 03 — Le function calling natif

À l'étape 02, on a inventé notre propre protocole pour que le modèle demande des outils.
Ici, on utilise le mécanisme **intégré à l'API** : le function calling.

## Objectifs

- Décrire un outil avec un **schéma JSON** (nom, description, paramètres)
- Lire une demande d'outil dans **`message.tool_calls`**
- Renvoyer un résultat avec le **rôle `tool`** et le **`tool_call_id`**
- Gérer **plusieurs outils** demandés dans une même réponse

## Fichiers

| Fichier | Rôle |
|---|---|
| `outils_cabinet.py` | Les mêmes outils qu'à l'étape 02 (fonctions Python sur `agenda.json`) |
| `schemas_outils.py` | La description des outils au format de l'API |
| `01_premier_tool_call.py` | Observer la demande brute du modèle, sans rien exécuter |
| `02_chat_function_calling.py` | Le chat de l'étape 02, réécrit en function calling |

## Comparaison avec l'étape 02

| | Étape 02 (fait maison) | Étape 03 (natif) |
|---|---|---|
| Description des outils | Texte dans le system prompt | Schéma JSON via `tools=` |
| Demande d'outil | JSON dans le texte, à détecter | Champ `message.tool_calls` |
| Retour du résultat | Message `user` avec `[RESULTAT OUTIL]` | Message `role: "tool"` + `tool_call_id` |
| Plusieurs outils à la fois | Non | Oui |
| `finish_reason` | `stop` | `tool_calls` |

## À retenir

- Le principe ne change pas : le modèle **demande**, notre code **exécute**.
- Les arguments arrivent sous forme de **chaîne JSON** : il faut les décoder et les vérifier.
- La qualité des **descriptions** dans le schéma influence directement les choix du modèle.
- Ici encore, un seul tour d'outils par question : impossible de chercher **puis** réserver
  sans redemander. Le function calling rend les outils fiables et parallélisables, mais tant qu’on ne laisse pas le modèle enchaîner les appels, il ne peut pas mener une tâche en plusieurs étapes. ➡️ Étape suivante : la **boucle agent**.
