"""
garde_fous.py
-------------
Les protections utilisées autour de l'équipe d'agents :

    ENTRÉE  : détection d'urgence (mots-clés), masquage des données personnelles
    SORTIE  : garde-fou CrewAI sur la réponse finale (termes médicaux, longueur)

La validation humaine des actions sur l'agenda est faite dans le script de l'équipe,
avec un hook CrewAI exécuté avant chaque appel d'outil.

Ce fichier n'est pas lancé directement : il est importé par les autres scripts du dossier.
"""

import re

# =============================================================================
# ENTRÉE
# =============================================================================
MOTS_URGENCE_VITALE = [
    "douleur thoracique", "douleur dans la poitrine", "mal à la poitrine", "serre dans la poitrine",
    "mal à respirer", "difficulté à respirer", "n'arrive plus à respirer", "étouffe",
    "malaise", "perte de connaissance", "inconscient", "évanoui",
    "avc", "paralysé", "bouche déformée", "saigne beaucoup", "hémorragie",
]
MOTS_DETRESSE = ["suicide", "me suicider", "envie de mourir", "en finir avec la vie"]

REPONSE_URGENCE_VITALE = ("⚠️ Ce que vous décrivez peut être une urgence vitale. "
                          "Appelez immédiatement le 15 (SAMU) ou le 112.")
REPONSE_DETRESSE = ("Je suis désolé que vous traversiez un moment aussi difficile. "
                    "Vous pouvez appeler le 3114, numéro national de prévention du suicide, "
                    "gratuit et disponible 24h/24. En cas de danger immédiat, appelez le 15.")


def detecter_urgence(texte):
    """Renvoie un message d'urgence si le texte contient un mot-clé, sinon None."""
    texte = texte.lower()
    if any(mot in texte for mot in MOTS_DETRESSE):
        return REPONSE_DETRESSE
    if any(mot in texte for mot in MOTS_URGENCE_VITALE):
        return REPONSE_URGENCE_VITALE
    return None


MOTIFS_DONNEES_PERSONNELLES = [
    ("NUMERO_SECU", re.compile(r"\b[12][\s.]?\d{2}[\s.]?\d{2}[\s.]?(?:\d{2}|2A|2B)[\s.]?\d{3}[\s.]?\d{3}[\s.]?\d{2}\b")),
    ("TELEPHONE", re.compile(r"(?:\+33\s?|\b0)[1-9](?:[\s.-]?\d{2}){4}\b")),
    ("EMAIL", re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")),
]


def masquer_donnees_personnelles(texte):
    """Remplace les données personnelles par un marqueur. Renvoie (texte masqué, types trouvés)."""
    trouvees = []
    for nom, motif in MOTIFS_DONNEES_PERSONNELLES:
        if motif.search(texte):
            trouvees.append(nom)
            texte = motif.sub(f"[{nom}_MASQUÉ]", texte)
    return texte, trouvees


# =============================================================================
# SORTIE
# =============================================================================
MOTS_INTERDITS = ["paracétamol", "ibuprofène", "doliprane", "antibiotique", "posologie", "diagnostic"]
MAX_PHRASES = 8
MAX_CARACTERES = 1500


def compter_phrases(texte):
    """Compte les phrases : morceaux de texte terminés par un point, ! ou ?."""
    texte = re.sub(r"\[[^\]]*\]", "", texte)   # les sources entre crochets ne comptent pas
    return len([p for p in re.split(r"[.!?]+(?:\s|$)", texte) if p.strip()])


def verifier_reponse(sortie):
    """Garde-fou CrewAI : (True, sortie) si la réponse est acceptable,
    sinon (False, message décrivant précisément le problème)."""
    texte = sortie.raw
    interdits = [mot for mot in MOTS_INTERDITS if mot in texte.lower()]
    if interdits:
        return False, (f"La réponse contient des termes médicaux interdits : {interdits}. "
                       "Reformule sans aucun conseil médical.")
    phrases = compter_phrases(texte)
    if phrases > MAX_PHRASES:
        return False, (f"La réponse contient {phrases} phrases, le maximum est {MAX_PHRASES}. "
                       "Supprime les phrases les moins utiles.")
    if len(texte) > MAX_CARACTERES:
        return False, (f"La réponse fait {len(texte)} caractères, le maximum est {MAX_CARACTERES}. "
                       "Raccourcis les phrases et cite les sources par le seul nom du fichier.")
    return True, sortie
