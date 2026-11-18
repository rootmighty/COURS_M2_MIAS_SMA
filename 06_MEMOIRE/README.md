# 06 — La mémoire

Un LLM n'a aucune mémoire entre deux appels (étape 00) : c'est notre code qui renvoie
l'historique. Cette étape distingue deux mémoires et leurs limites.

## Objectifs

- Mesurer la **croissance de l'historique** (tokens envoyés à chaque appel)
- Gérer la **mémoire courte** : historique complet, fenêtre glissante, résumé
- Construire une **mémoire longue** qui survit d'une conversation à l'autre
- Réfléchir à **ce qu'on a le droit de retenir** (RGPD, données de santé)

## Fichiers

| Fichier | Rôle |
|---|---|
| `agent.py` | La boucle agent rangée dans un module, avec une sortie propre à la limite d'étapes |
| `outils_cabinet.py`, `schemas_outils.py` | Les outils de l'agenda (dont `deplacer_rdv`) |
| `01_memoire_courte.py` | Chat avec 3 stratégies d'historique et affichage des tokens |
| `memoire_patients.py` | Les outils de mémoire longue (fichier `memoire_patients.json`) |
| `02_memoire_longue.py` | L'agent se souvient des préférences d'un patient entre deux sessions |

## Améliorations issues de l'étape 05

L'agent multi-serveurs s'était perdu dans 16 recherches et n'avait rien répondu. Deux corrections :

- **Critère d'arrêt** dans le prompt (`CRITERE_ARRET`) : après 2 ou 3 essais infructueux,
  répondre avec ce qui a été trouvé.
- **Sortie propre** dans `agent.py` : à la limite d'étapes, un dernier appel avec
  `tool_choice="none"` oblige le modèle à répondre avec les informations déjà collectées,
  au lieu d'un message d'échec générique.

## Les deux mémoires

| | Mémoire courte | Mémoire longue |
|---|---|---|
| Contenu | L'historique de la conversation | Des informations choisies sur le patient |
| Durée | Le temps de la session | D'une session à l'autre |
| Stockage | Une liste Python (`messages`) | Un fichier (ici JSON ; en pratique une base de données) |
| Problème | Grossit à chaque échange | Que retenir ? Qui peut y accéder ? |

## Stratégies de mémoire courte

| Stratégie | Principe | Avantage | Inconvénient |
|---|---|---|---|
| `complete` | Tout garder | Rien n'est oublié | Coût et taille qui augmentent sans fin |
| `fenetre` | Garder les N derniers échanges | Taille constante, simple | Oubli brutal des premiers échanges |
| `resume` | Résumer l'ancien, garder le récent | Taille maîtrisée, l'essentiel est gardé | Un appel au LLM en plus, détails perdus |

## À retenir

- La mémoire d'un agent, c'est **ce qu'on choisit de lui renvoyer**.
- On coupe toujours l'historique **entre deux échanges**, jamais entre une demande
  d'outil et son résultat.
- La mémoire longue peut être un **outil** : l'agent décide quoi lire et quoi écrire.
- En santé, la mémoire est une **donnée personnelle** : minimisation, interdiction des
  données médicales non nécessaires, droit à l'effacement. ➡️ Étape suivante : les **guardrails**.
