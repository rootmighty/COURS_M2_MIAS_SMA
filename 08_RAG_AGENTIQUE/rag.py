"""
rag.py
------
Les briques du RAG (Retrieval-Augmented Generation) :

    1. découper les documents en morceaux        (decouper_documents)
    2. transformer des textes en vecteurs         (embedder)
    3. construire et sauvegarder un index FAISS   (construire_index)
    4. retrouver les morceaux les plus proches    (rechercher)

Les vecteurs (embeddings) sont calculés par un modèle d'embedding de l'API NVIDIA.
FAISS stocke ces vecteurs et retrouve très vite les plus proches d'une question.

Ce fichier n'est pas lancé directement : il est importé par les autres scripts du dossier.

Prérequis :
    pip install faiss-cpu numpy
"""

import json
import os
import re
import time
from pathlib import Path

import faiss
import numpy as np
from openai import APIStatusError, APITimeoutError

from agent import client

# Client dédié aux embeddings : délai d'attente plus long et plus de réessais,
# car l'API gratuite peut ralentir quand on envoie beaucoup de requêtes à la suite
client_embedding = client.with_options(timeout=120, max_retries=5)

# --- Configuration ---------------------------------------------------------
# Modèle d'embedding multilingue de l'API NVIDIA (modifiable dans le .env)
MODELE_EMBEDDING = os.getenv("NVIDIA_EMBEDDING_MODEL", "nvidia/nemotron-3.5-embed-1b")

DOSSIER = Path(__file__).parent
DOSSIER_DOCUMENTS = DOSSIER / "documents"
DOSSIER_INDEX = DOSSIER / "index_faiss"
FICHIER_INDEX = DOSSIER_INDEX / "index.faiss"
FICHIER_MORCEAUX = DOSSIER_INDEX / "morceaux.json"

TAILLE_MAX_MORCEAU = 1000   # nombre maximum de caractères par morceau
TAILLE_LOT = 16             # nombre de textes envoyés par appel à l'API d'embedding
PAUSE_ENTRE_LOTS = 1        # secondes d'attente entre deux appels à l'API d'embedding


# --- 1. Découpage des documents --------------------------------------------------
def regrouper_phrases(texte, taille_max):
    """Découpe un texte en morceaux d'au plus taille_max caractères, sans couper de phrase.

    Les phrases sont ajoutées une à une au morceau en cours ; quand la suivante
    ferait dépasser taille_max, un nouveau morceau commence.
    Une phrase plus longue que taille_max forme un morceau à elle seule.
    """
    # Coupure après un point, un point d'exclamation ou d'interrogation suivi d'un espace
    phrases = re.split(r"(?<=[.!?])\s+", texte)
    parties, courante = [], ""
    for phrase in phrases:
        if courante and len(courante) + 1 + len(phrase) > taille_max:
            parties.append(courante)
            courante = phrase
        else:
            courante = f"{courante} {phrase}".strip()
    if courante:
        parties.append(courante)
    return parties


def decouper_documents():
    """Découpe chaque document Markdown en morceaux, un par section (titre "## ").

    Chaque morceau est un dictionnaire :
        {"source": "faq_cabinet.md", "section": "Retards", "texte": "..."}
    Le titre du document et de la section sont ajoutés au texte : ils aident
    à retrouver le morceau et à comprendre son contexte.
    """
    morceaux = []
    for fichier in sorted(DOSSIER_DOCUMENTS.glob("*.md")):
        lignes = fichier.read_text(encoding="utf-8").splitlines()
        titre_document = lignes[0].lstrip("# ").strip() if lignes else fichier.stem
        section, contenu = None, []

        def ajouter_section():
            """Ajoute la section en cours, découpée en morceaux si elle est trop longue."""
            texte = " ".join(l for l in contenu if l.strip())
            if not section or not texte:
                return
            for partie in regrouper_phrases(texte, TAILLE_MAX_MORCEAU):
                morceaux.append({
                    "source": fichier.name,
                    "section": section,
                    "texte": f"{titre_document} — {section}\n{partie}",
                })

        for ligne in lignes[1:]:
            if ligne.startswith("## "):   # nouvelle section : on enregistre la précédente
                ajouter_section()
                section, contenu = ligne[3:].strip(), []
            else:
                contenu.append(ligne)
        ajouter_section()   # dernière section du fichier

    return morceaux


# --- 2. Embeddings ------------------------------------------------------------------
def embedder(textes, type_entree):
    """Transforme une liste de textes en vecteurs (tableau numpy, une ligne par texte).

    type_entree : "passage" pour les documents indexés, "query" pour les questions.
    Le modèle encode différemment les deux, ce qui améliore la recherche.
    """
    vecteurs = []
    nombre_lots = (len(textes) + TAILLE_LOT - 1) // TAILLE_LOT   # division arrondie au-dessus
    for numero, debut in enumerate(range(0, len(textes), TAILLE_LOT), start=1):
        lot = textes[debut:debut + TAILLE_LOT]
        if nombre_lots > 1:
            print(f"   Embeddings : lot {numero}/{nombre_lots} ({len(lot)} textes)", flush=True)
            if numero > 1:
                time.sleep(PAUSE_ENTRE_LOTS)   # on espace les appels pour ménager l'API
        try:
            reponse = client_embedding.embeddings.create(
                model=MODELE_EMBEDDING,
                input=lot,
                encoding_format="float",
                # Paramètres propres à l'API NVIDIA, transmis tels quels
                extra_body={"input_type": type_entree, "truncate": "END"},
            )
        except APIStatusError as e:
            # 404 : modèle inconnu / 410 : modèle retiré du catalogue
            if e.status_code in (404, 410):
                raise SystemExit(
                    f"Le modèle d'embedding '{MODELE_EMBEDDING}' n'est pas disponible "
                    f"(erreur {e.status_code}). Choisissez un modèle d'embedding sur "
                    "build.nvidia.com et indiquez-le dans le .env : NVIDIA_EMBEDDING_MODEL=..."
                ) from None
            raise
        except APITimeoutError:
            raise SystemExit(
                "L'API d'embedding ne répond pas (délai dépassé, même après plusieurs essais). "
                "Réessayez dans quelques minutes, ou réduisez TAILLE_LOT dans rag.py."
            ) from None
        vecteurs.extend(element.embedding for element in reponse.data)

    vecteurs = np.array(vecteurs, dtype="float32")
    # Normalisation : chaque vecteur a une longueur de 1.
    # Le produit scalaire entre deux vecteurs normalisés est leur similarité cosinus.
    faiss.normalize_L2(vecteurs)
    return vecteurs


# --- 3. Index FAISS -------------------------------------------------------------------
def construire_index():
    """Découpe les documents, calcule les embeddings et sauvegarde l'index FAISS."""
    morceaux = decouper_documents()
    vecteurs = embedder([m["texte"] for m in morceaux], "passage")

    # IndexFlatIP : recherche exacte par produit scalaire (Inner Product)
    index = faiss.IndexFlatIP(vecteurs.shape[1])
    index.add(vecteurs)

    DOSSIER_INDEX.mkdir(exist_ok=True)
    faiss.write_index(index, str(FICHIER_INDEX))
    FICHIER_MORCEAUX.write_text(json.dumps(morceaux, indent=2, ensure_ascii=False), encoding="utf-8")
    return index, morceaux


def charger_index():
    """Charge l'index FAISS et les morceaux sauvegardés."""
    if not FICHIER_INDEX.exists():
        raise FileNotFoundError("Index introuvable : lancez d'abord 02_indexer_documents.py")
    index = faiss.read_index(str(FICHIER_INDEX))
    morceaux = json.loads(FICHIER_MORCEAUX.read_text(encoding="utf-8"))
    return index, morceaux


# --- 4. Recherche ---------------------------------------------------------------------
_index, _morceaux = None, None   # index chargé une seule fois, au premier appel


def rechercher(question, k=3):
    """Renvoie les k morceaux les plus proches de la question, avec leur score (0 à 1)."""
    global _index, _morceaux
    if _index is None:
        _index, _morceaux = charger_index()

    vecteur_question = embedder([question], "query")
    # search renvoie les scores et les positions des k vecteurs les plus proches
    scores, positions = _index.search(vecteur_question, k)

    return [
        {**_morceaux[position], "score": round(float(score), 3)}
        for score, position in zip(scores[0], positions[0])
        if position != -1
    ]
