"""
01_embeddings.py
----------------
Qu'est-ce qu'un embedding ? Un vecteur de nombres qui représente le SENS d'un texte.

Deux textes de sens proche ont des vecteurs proches, même s'ils n'ont aucun mot en commun.
On mesure cette proximité avec la similarité cosinus (de -1 à 1, 1 = même sens).

On compare ici trois questions de patients à quatre extraits de documents du cabinet :
    - par mots communs (comme la recherche par mots-clés de data.gouv.fr) ;
    - par similarité des embeddings (recherche sémantique).

Lancement :
    python 08_RAG_AGENTIQUE/01_embeddings.py

EXERCICES :
    1. Pour chaque question, quel extrait obtient le meilleur score ? Est-ce le bon ?
    2. La question "Où puis-je garer ma voiture ?" partage-t-elle des mots avec le bon extrait ?
    3. Posez une question en anglais. Le bon extrait est-il toujours trouvé ?
    4. Combien de nombres contient un vecteur ? Qu'en déduire sur le stockage d'un gros corpus ?
"""

import re

from rag import MODELE_EMBEDDING, embedder

QUESTIONS = [
    "Où puis-je garer ma voiture ?",
    "Est-ce que je peux régler par chèque ?",
    "Je n'arrive pas à venir, comment je fais pour annuler ?",
]

EXTRAITS = [
    "Un parking gratuit de six places est disponible dans la cour intérieure.",
    "Le cabinet accepte la carte bancaire et les espèces. Les chèques ne sont plus acceptés.",
    "Merci d'annuler votre rendez-vous au moins 24 heures à l'avance.",
    "La téléconsultation est réservée aux patients déjà reçus au cabinet.",
]


def mots(texte):
    """Ensemble des mots d'un texte, en minuscules (sans les mots de moins de 3 lettres)."""
    return {m for m in re.findall(r"\w+", texte.lower()) if len(m) > 2}


# Embeddings : "query" pour les questions, "passage" pour les extraits
vecteurs_questions = embedder(QUESTIONS, "query")
vecteurs_extraits = embedder(EXTRAITS, "passage")

print(f"Modèle : {MODELE_EMBEDDING}")
print(f"Taille d'un vecteur : {vecteurs_extraits.shape[1]} nombres")
print(f"Début du vecteur du 1er extrait : {vecteurs_extraits[0][:5].round(3)} ...\n")

# Matrice des similarités : produit scalaire des vecteurs normalisés = similarité cosinus
similarites = vecteurs_questions @ vecteurs_extraits.T

for i, question in enumerate(QUESTIONS):
    print("=" * 70)
    print(f"QUESTION : {question}\n")
    for j, extrait in enumerate(EXTRAITS):
        communs = mots(question) & mots(extrait)
        print(f"  similarité {similarites[i, j]:.3f} | mots communs : {len(communs)} {sorted(communs)}")
        print(f"     {extrait}")
    meilleur = similarites[i].argmax()
    print(f"\n  -> Extrait le plus proche : {EXTRAITS[meilleur]}\n")
