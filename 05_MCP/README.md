# 05 — MCP (Model Context Protocol)

Jusqu'ici, les outils vivaient **dans** notre programme : fonctions importées,
schémas écrits à la main. Avec MCP, les outils deviennent un **service séparé**,
qu'on peut brancher sur n'importe quel agent ou application d'IA.

## Objectifs

- **Construire** un serveur MCP qui expose les outils de l'agenda
- **Découvrir** les outils d'un serveur depuis un client
- Brancher la **boucle agent** sur un serveur MCP
- **Consommer** un serveur MCP public : celui de data.gouv.fr
- Connecter un agent à **plusieurs serveurs** à la fois

## Fichiers

| Fichier | Rôle |
|---|---|
| `outils_cabinet.py` | Les outils, avec un nouveau : `deplacer_rdv` (réserver avant d'annuler) |
| `serveur_agenda.py` | Le serveur MCP de l'agenda (lancé automatiquement par les clients) |
| `01_inspecter_serveur.py` | Client sans IA : lister les outils, en appeler un |
| `02_agent_mcp.py` | La boucle agent de l'étape 04, branchée sur le serveur MCP |
| `03_inspecter_datagouv.py` | Se connecter au serveur public de data.gouv.fr |
| `04_agent_multi_serveurs.py` | Un agent connecté à l'agenda **et** à data.gouv.fr |

## Installation

```bash
pip install mcp
```

Les scripts utilisent la version 2 du SDK Python MCP (`from mcp import Client`,
`MCPServer`). Ajoutez `mcp>=2` dans `requirements.txt`.

## Ce qui change par rapport à l'étape 04

| | Étape 04 | Étape 05 (MCP) |
|---|---|---|
| Schémas des outils | Écrits à la main (`schemas_outils.py`) | Générés par le serveur à partir des fonctions |
| Découverte des outils | Codée en dur | `list_tools()` auprès du serveur |
| Exécution | Dans le programme de l'agent | Dans le serveur MCP |
| Réutilisation | Propre à notre agent | Tout client MCP (Claude Desktop, IDE, autre agent…) |

Tester dans le browser: 
```bash
npx @modelcontextprotocol/inspector python 05_MCP/serveur_agenda.py
```
## À retenir

- MCP sépare **l'agent** (qui raisonne) des **outils** (qui agissent).
- Un serveur MCP n'a **pas d'IA** : il expose des outils, c'est tout.
- Le même client se connecte à un serveur **local** (stdio) ou **distant** (URL).
- `deplacer_rdv` montre qu'une logique critique (réserver avant d'annuler,
  revenir en arrière en cas d'échec) se met **dans l'outil**, pas dans le prompt.
- Brancher un serveur, c'est lui faire **confiance** : ses descriptions et ses résultats
  arrivent dans le contexte de l'agent. On n'utilise que des serveurs connus et officiels.
- Plus de serveurs = plus d'outils = un prompt plus long et des résultats parfois volumineux.
