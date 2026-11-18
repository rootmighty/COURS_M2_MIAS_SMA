# 04 — La boucle agent

À l'étape 03, Doc'Assist ne pouvait exécuter qu'un tour d'outils par question :
« chercher **puis** réserver » échouait. Ici, on le laisse **enchaîner** les outils
jusqu'à terminer sa tâche. C'est ce qui fait passer d'un chatbot outillé à un **agent**.

## Objectifs

- Écrire la **boucle agent** : appeler le modèle tant qu'il demande des outils
- Protéger la boucle avec une **limite d'étapes**
- Comprendre le schéma **ReAct** : Pensée → Action → Observation
- Voir un agent mener seul une tâche en **plusieurs étapes dépendantes**

## Fichiers

| Fichier | Rôle |
|---|---|
| `outils_cabinet.py` | Les outils, avec deux nouveaux : `lister_rdv` et `annuler_rdv` |
| `schemas_outils.py` | Les schémas des quatre outils |
| `01_boucle_agent.py` | Le chat de l'étape 03, avec la boucle agent |
| `02_react_explicite.py` | Tâche autonome (déplacer un RDV) avec la trace Pensée / Action / Observation |

## Ce qui change par rapport à l'étape 03

Un `if` devient un `for` :

```python
for etape in range(MAX_ETAPES):
    message = appeler_llm(messages)
    if not message.tool_calls:      # plus d'outil demandé : tâche terminée
        return message.content
    ...                             # exécuter les outils, ajouter les résultats, recommencer
```

## À retenir

- **Agent = LLM + outils + boucle.** C'est le modèle qui décide quand il a fini.
- La limite `MAX_ETAPES` est indispensable : sans elle, un agent qui se trompe
  peut tourner longtemps, et chaque tour coûte du temps et des tokens.
- L'historique grossit à chaque étape : tous les résultats d'outils y restent.
- L'agent agit **seul** : dans `02`, il réserve et annule sans demander confirmation.
  Pratique, mais risqué. ➡️ On y reviendra avec les **guardrails** et la validation humaine.
- Ce que l'on vient d'écrire à la main, c'est exactement ce que font CrewAI et
  les autres frameworks sous le capot.
