"""
02_indexer_documents.py
-----------------------
Indexation : préparer les documents du cabinet pour la recherche.

    documents/*.md ──> découpage en morceaux ──> embeddings ──> index FAISS (sauvegardé)

L'indexation se fait UNE fois (ou à chaque modification des documents).
Les recherches utilisent ensuite l'index sauvegardé dans index_faiss/.

Lancement :
    python 08_RAG_AGENTIQUE/02_indexer_documents.py

EXERCICES :
    1. Combien de morceaux ont été créés ? Ouvrez index_faiss/morceaux.json.
    2. Ajoutez un document dans documents/ (ex. vaccination.md), relancez, et testez une question.
    3. Passez TAILLE_MAX_MORCEAU à 200 dans rag.py. Les résultats sont-ils meilleurs ou pires ?
"""

from rag import FICHIER_INDEX, construire_index, rechercher

# --- Indexation -------------------------------------------------------------------
index, morceaux = construire_index()

print(f"{len(morceaux)} morceaux indexés, vecteurs de {index.d} dimensions.")
print(f"Index sauvegardé : {FICHIER_INDEX}\n")
for morceau in morceaux:
    print(f"  - {morceau['source']:32} | {morceau['section']}")

# --- Test de recherche -------------------------------------------------------------
QUESTION_TEST = "Mon médecin est en vacances, qui me soigne ?"
print(f"\nTest : {QUESTION_TEST}")
for resultat in rechercher(QUESTION_TEST, k=3):
    print(f"  {resultat['score']:.3f} | {resultat['source']} — {resultat['section']}")
