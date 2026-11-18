"""
03_rag_classique.py
-------------------
Le RAG classique : à chaque question, le CODE cherche dans les documents
et ajoute les extraits trouvés au prompt, puis le LLM répond.

    question ──> recherche FAISS (toujours) ──> extraits + question ──> LLM ──> réponse

Prérequis : avoir lancé 02_indexer_documents.py

Lancement :
    python 08_RAG_AGENTIQUE/03_rag_classique.py

EXERCICES :
    1. Les réponses citent-elles leurs sources ? Sont-elles exactes ?
    2. Que répond le modèle pour l'acupuncture, absente des documents ?
    3. "Bonjour !" : la recherche était-elle utile ? Et pour le créneau de demain ?
    4. Passez K à 1, puis à 6. Quel effet sur les réponses et sur le nombre de tokens ?
"""

from agent import appeler_llm, tokens_contexte
from rag import rechercher

K = 3   # nombre d'extraits ajoutés au prompt

QUESTIONS = [
    "Je peux payer par chèque ?",
    "Que se passe-t-il si j'arrive avec 20 minutes de retard ?",
    "Comment obtenir une copie de mon dossier médical ?",
    "Je ne suis pas venu depuis deux ans, je peux faire une téléconsultation ?",
    "Le Dr Martin fait-il de l'acupuncture ?",
    "Bonjour !",
    "Il vous reste un créneau demain matin ?",
]

CONSIGNE = """Tu es Doc'Assist, l'assistant de secrétariat du cabinet du Dr Martin.
Réponds à la question du patient UNIQUEMENT à partir des extraits de documents ci-dessous.
Cite la source de chaque information entre crochets, par exemple [faq_cabinet.md — Retards].
Si les extraits ne contiennent pas la réponse, dis simplement que tu n'as pas cette information
et propose de contacter le secrétariat. Ton ton est chaleureux et concis.

EXTRAITS :
{extraits}"""


def formater_extraits(resultats):
    """Met en forme les extraits trouvés pour les insérer dans le prompt."""
    return "\n\n".join(f"[{r['source']} — {r['section']}]\n{r['texte']}" for r in resultats)


for question in QUESTIONS:
    print("=" * 70)
    print(f"PATIENT : {question}")

    # 1. Recherche : systématique, quelle que soit la question
    resultats = rechercher(question, k=K)
    for r in resultats:
        print(f"   🔎 {r['score']:.3f} | {r['source']} — {r['section']}")

    # 2. Génération : les extraits sont injectés dans le system prompt
    completion = appeler_llm([
        {"role": "system", "content": CONSIGNE.format(extraits=formater_extraits(resultats))},
        {"role": "user", "content": question},
    ])
    print(f"DOC'ASSIST : {completion.choices[0].message.content}")
    print(f"   📊 {tokens_contexte(completion)} tokens envoyés\n")
