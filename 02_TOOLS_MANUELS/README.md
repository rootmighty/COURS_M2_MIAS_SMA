# 02 — Les outils, à la main

Doc'Assist sait parler et structurer ses réponses, mais il ne **voit pas l'agenda**.
Dans cette étape, on lui donne des outils… sans aucune magie : on code tout nous-mêmes.

## Objectifs

- Comprendre qu'un LLM **ne peut pas agir** : il ne fait que produire du texte
- Constater qu'il **hallucine** quand il lui manque une information
- Comprendre le mécanisme d'un outil : le modèle **demande**, notre code **exécute**
- Voir les limites d'un protocole « fait maison »

## Fichiers

| Fichier | Rôle |
|---|---|
| `outils_cabinet.py` | Les outils : fonctions Python classiques sur `agenda.json` (aucune IA) |
| `01_le_probleme.py` | Sans outil, le modèle invente des disponibilités |
| `02_outils_manuels.py` | Chat où le modèle demande des outils via un JSON défini dans le prompt |

L'agenda (`agenda.json`) est créé automatiquement pour les 14 prochains jours ouvrés.
Pour le remettre à zéro : `python 02_TOOLS_MANUELS/outils_cabinet.py --reset`

## À retenir

- Le modèle ne fait que **demander** un outil. C'est **notre code** qui l'exécute
  et qui reste maître de ce qui se passe : vérification de la date, du créneau, etc.
- Les erreurs des outils sont **renvoyées au modèle**, qui peut les expliquer au patient.
- Ce protocole fonctionne, mais il est fragile : le modèle peut mal formater son JSON,
  mélanger texte et JSON, inventer un nom d'outil… Et la description des outils
  prend de la place dans le prompt.
- Ici, un seul outil par question : impossible de chercher **puis** réserver d'un coup.

➡️ Étape suivante : le **function calling** natif, où l'API gère tout ça proprement.
