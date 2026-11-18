# 07 — Les guardrails

Un agent qui agit seul, avec une mémoire et des données de santé, doit être protégé.
Les règles du system prompt orientent le modèle, mais ne garantissent rien.
Cette étape ajoute des **protections en code**, autour du modèle.

## Objectifs

- Tester un agent protégé **uniquement par son prompt**, face à des attaques simples puis élaborées
- Protéger l'**entrée** : urgences, données personnelles, injections de prompt
- Protéger les **outils** : identité imposée par le code, contrôle d'accès, quota, **validation humaine**
- Se protéger de l'**injection indirecte** : des instructions cachées dans les données lues par un outil
- Protéger la **sortie** : vérification par un **LLM juge**
- Mesurer le **coût** de la sécurité (appels, latence, faux positifs)

## Fichiers

| Fichier | Rôle |
|---|---|
| `agent.py` | La boucle agent, avec un contrôle optionnel avant chaque outil (`garde_outil`) |
| `outils_cabinet.py`, `schemas_outils.py` | Les outils de l'agenda et des informations pratiques |
| `guardrails.py` | Les protections des trois couches |
| `scenarios.py` | 16 scénarios de test, en deux séries : simple et avancée |
| `01_attaques_sans_protection.py` | Les scénarios face à un agent protégé par son seul prompt |
| `02_agent_avec_guardrails.py` | Les mêmes scénarios avec les trois couches de protection |

## Les scénarios

| Série simple | Série avancée |
|---|---|
| Demande légitime | Usurpation d'identité |
| Injection de prompt | Fausse autorité (« message du Dr Martin ») |
| Conseil médical | Cadre fictif (« pour former une secrétaire… ») |
| Urgence vitale | Pression émotionnelle (enfant fiévreux) |
| Données d'un autre patient | Extraction du prompt |
| Action sur un autre patient | Abus de fonctionnalité (réserver tous les créneaux) |
| Données personnelles dans le message | Attaque en plusieurs tours (« la nouvelle infirmière ») |
| Action sensible légitime | Injection indirecte (instruction cachée dans les informations pratiques) |

## Les trois couches

| Couche | Protection | Technique | Ce qu'elle bloque |
|---|---|---|---|
| Entrée | Urgence | Mots-clés | Signes d'urgence vitale, détresse → 15 / 3114 |
| Entrée | Données personnelles | Expressions régulières | N° de sécu, téléphone, e-mail envoyés au fournisseur |
| Entrée | Classification | LLM | Injection, conseil médical, hors sujet |
| Outils | Identité imposée | Code | Le modèle ne peut plus choisir (ni mal écrire) le nom du patient |
| Outils | Contrôle d'accès | Code | Toute tentative de viser un autre patient |
| Outils | Quota | Code | Réservations abusives |
| Outils | Validation humaine | `input()` | Annulations et déplacements non voulus |
| Outils | Encadrement | Code + prompt | Instructions cachées dans des données de tiers |
| Sortie | Juge | LLM | Conseil médical, fuite d'informations, affirmations suspectes |

## À retenir

- **Le prompt rend l'agent poli ; seul le code le rend sûr.** Un modèle peut résister à une
  attaque 9 fois sur 10, et céder la dixième, ou après un changement de modèle.
- **Défense en profondeur** : plusieurs couches imparfaites valent mieux qu'une seule.
- Ce qui est **critique** ne se confie pas au modèle : l'identité du patient est fournie
  par le code, pas devinée par le LLM.
- L'**injection indirecte** est le risque n°1 des agents : toute donnée lue par un outil
  (note, e-mail, page web, mémoire, serveur MCP) peut contenir des instructions.
- Les actions **irréversibles** passent par une **validation humaine**.
- Certaines fuites ont lieu **avant** toute réponse : un numéro de sécu envoyé au
  fournisseur est déjà parti, même si le modèle répond parfaitement.
- La sécurité a un prix : une demande légitime passe par **au moins 3 appels au LLM**
  (classification, agent, juge), avec un risque de **faux positifs**.
