"""
indexer_documents.py
--------------------
Construit l'index FAISS des documents du cabinet (dossier index_faiss/).

L'index est construit automatiquement à la première recherche, mais il est
préférable de le préparer à l'avance : la construction appelle l'API d'embedding
plusieurs fois, et cette API peut être surchargée (erreur 503).

Lancement :
    python 09_CREWAI_SMA/indexer_documents.py
"""

from rag import FICHIER_INDEX, construire_index

index, morceaux = construire_index()
print(f"{len(morceaux)} morceaux indexés, vecteurs de {index.d} dimensions.")
print(f"Index sauvegardé : {FICHIER_INDEX}")
