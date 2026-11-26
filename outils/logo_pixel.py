"""Logo de Centrale Lyon en pixel art, animé, pour le profil GitHub.

Script écrit avec Claude Code (Anthropic), modèle Claude Fable 5.2, le 25/11/2026.
Modifié le 26/11/2026 (modèle Claude Fable 5.2) : 33 images par seconde, mouvements
adoucis, apparitions en fondu tramé.
Le logo appartient à l'École Centrale de Lyon. Ce fichier n'en fait qu'un dessin
en pixels pour un profil d'élève.

Lancer :
    python outils/logo_pixel.py

Le script écrit deux GIF dans assets/ :
    centrale-lyon-pixel-clair.gif    (texte rouge, pour le thème clair de GitHub)
    centrale-lyon-pixel-sombre.gif   (texte blanc, pour le thème sombre)

Principe : le logo est dessiné sur une grille de « gros pixels » (186 x 88).
Un gros pixel vaut ECHELLE x ECHELLE pixels du GIF. Les formes restent sur la
grille, mais elles bougent au pixel réel près : c'est ce qui rend le mouvement
fluide. Chaque image est un tableau de petits entiers (un entier = une couleur).
"""

import math
from pathlib import Path

import numpy as np
from PIL import Image

# --------------------------------------------------------------------------
# Réglages généraux
# --------------------------------------------------------------------------

LARGEUR, HAUTEUR = 186, 88   # taille de la grille, en gros pixels
ECHELLE = 4                  # 1 gros pixel = 4 x 4 pixels dans le GIF
DUREE_IMAGE_MS = 30          # 30 ms par image = 33 images par seconde

# Numéros de couleur dans la palette
VIDE, ROUGE, BLANC, TEXTE, REFLET, REFLET_FORT, REFLET_TEXTE, AILE, OR = range(9)

ROUGE_CENTRALE = (178, 33, 51)   # mesuré sur le logo fourni

PALETTES = {
    "clair": {
        VIDE: (0, 0, 0),                 # jamais affichée : couleur transparente
        ROUGE: ROUGE_CENTRALE,
        BLANC: (255, 255, 255),
        TEXTE: ROUGE_CENTRALE,
        REFLET: (226, 104, 120),         # rouge éclairci
        REFLET_FORT: (250, 196, 203),    # cœur du reflet, presque blanc
        REFLET_TEXTE: (226, 104, 120),
        AILE: (232, 150, 160),
        OR: (206, 160, 72),              # la pointe qui trace, les étincelles
    },
    "sombre": {
        VIDE: (0, 0, 0),
        ROUGE: ROUGE_CENTRALE,
        BLANC: (255, 255, 255),
        TEXTE: (255, 255, 255),
        REFLET: (226, 104, 120),
        REFLET_FORT: (250, 196, 203),
        REFLET_TEXTE: (255, 200, 207),
        AILE: (232, 150, 160),
        OR: (214, 170, 84),
    },
}

# --------------------------------------------------------------------------
# Le blason (coordonnées locales : 55 colonnes x 72 lignes)
# --------------------------------------------------------------------------

BX, BY = 8, 8          # position du coin haut-gauche du blason dans la grille
BL, BH = 55, 72        # largeur et hauteur du blason
AXE = 27               # colonne du milieu (trait vertical)
BAS_BANDE = 32         # dernière ligne de la bande rouge du haut

# De combien le bord rentre vers l'intérieur, ligne par ligne, de 52 à 71
RETRAITS_POINTE = [0, 1, 1, 2, 2, 3, 4, 5, 6, 7, 9, 11, 13, 15, 17, 19, 21, 23, 25, 26]


def construire_blason():
    """Renvoie trois masques (tableaux de True/False) : forme, contour, intérieur."""
    forme = np.zeros((BH, BL), dtype=bool)
    for y in range(BH):
        retrait = RETRAITS_POINTE[y - 52] if y >= 52 else 0
        for x in range(retrait, BL - retrait):
            ecart = abs(x - AXE)
            haut_arrondi = round(6 * (ecart / AXE) ** 2)   # le haut est bombé
            if y >= haut_arrondi:
                forme[y, x] = True

    # Contour : cases de la forme qui touchent l'extérieur (haut, bas, gauche, droite)
    large = np.pad(forme, 1)
    voisins_dedans = large[:-2, 1:-1] & large[2:, 1:-1] & large[1:-1, :-2] & large[1:-1, 2:]
    contour = forme & ~voisins_dedans
    interieur = forme & ~contour
    return forme, contour, interieur


FORME, CONTOUR, INTERIEUR = construire_blason()

_ys, _xs = np.mgrid[0:BH, 0:BL]

# --------------------------------------------------------------------------
# Le lion (blanc sur la bande rouge). '#' = case blanche.
# --------------------------------------------------------------------------

LION_X, LION_Y = 5, 8   # position du lion dans le blason

LION_CORPS = [
    ".................................########....",
    "...............................###########...",
    "..............................############...",
    "............................###############..",
    "............................################.",
    "...........................##################",
    ".............################################",
    "..........##################################.",
    ".........################################....",
    "#......###..############################.....",
    "##....##....############################.....",
    "..####.....###########################.......",
    "..........###########################........",
    "..........###########################........",
    ".........############################........",
]

# Pattes écartées : c'est la pose du logo
PATTES_A = [
    ".....#########..####......############.......",
    ".....#######.....###......####.....####......",
    "....#####.........##......###.......####.....",
    "....##............###.....##.........####....",
    "....##............####....##..........#####..",
    ".....###............####..####...........###.",
]

# La queue du lion : trois positions. Chacune remplace les 10 premières
# colonnes des lignes 9 à 12 du corps. « haute » est la pose du logo.
QUEUES = {
    "haute": [
        "#......###",
        "##....##..",
        "..####....",
        "..........",
    ],
    "milieu": [
        ".......###",
        "......##..",
        "######....",
        "..........",
    ],
    "basse": [
        ".......###",
        "......##..",
        "...###....",
        "###.......",
    ],
}


def lignes_lion(queue):
    """Renvoie le dessin complet du lion pour une position de la queue."""
    corps = list(LION_CORPS)
    for i, debut in enumerate(QUEUES[queue]):
        corps[9 + i] = debut + corps[9 + i][10:]
    return corps + PATTES_A


# --------------------------------------------------------------------------
# Les abeilles, 11 x 10 cases. '#' = rouge, 'o' = rose clair (les ailes).
# --------------------------------------------------------------------------
# Vue de dessus, tête en haut à droite : un thorax plein, deux ailes,
# trois rayures pour l'abdomen. Sur le logo, les ailes sont des traits fins :
# à cette taille elles paraissent roses, d'où la couleur claire.

ABEILLE_AILES_OUVERTES = [
    ".oo......#.",
    ".ooo...##..",
    "..ooo.###..",
    "...oo###...",
    ".....##oo..",
    "...###.oooo",
    "........ooo",
    "..###......",
    "...........",
    ".###.......",
]

ABEILLE_AILES_FERMEES = [
    ".........#.",
    "..o....##..",
    "..oo..###..",
    "...oo###...",
    ".....##o...",
    "...###.ooo.",
    "...........",
    "..###......",
    "...........",
    ".###.......",
]

# Position (coin haut-gauche) des trois abeilles dans le blason
ABEILLES = [(2, 40), (15, 36), (13, 50)]

# --------------------------------------------------------------------------
# Les engrenages : (centre x, centre y, rayon, nombre de dents, sens, anneau intérieur)
# --------------------------------------------------------------------------

ENGRENAGES = [
    (37, 56, 6.0, 12, +1, 3.0),  # le grand, en bas
    (46, 48, 3.0, 6, -1, 0),     # le petit, au milieu
    (39, 40, 4.0, 8, +1, 0),     # celui du haut
]

# --------------------------------------------------------------------------
# Les lettres (13 lignes de haut, traits de 3 cases)
# --------------------------------------------------------------------------

LETTRES = {
    "C": [
        "..#######..",
        ".#########.",
        "###########",
        "###.....###",
        "###.....###",
        "###........",
        "###........",
        "###........",
        "###.....###",
        "###.....###",
        "###########",
        ".#########.",
        "..#######..",
    ],
    "E": [
        "##########",
        "##########",
        "##########",
        "###.......",
        "###.......",
        "#########.",
        "#########.",
        "#########.",
        "###.......",
        "###.......",
        "##########",
        "##########",
        "##########",
    ],
    "N": [
        "####.....###",
        "#####....###",
        "#####....###",
        "######...###",
        "######...###",
        "###.###..###",
        "###.###..###",
        "###..###.###",
        "###...######",
        "###...######",
        "###....#####",
        "###....#####",
        "###.....####",
    ],
    "T": [
        "###########",
        "###########",
        "###########",
        "....###....",
        "....###....",
        "....###....",
        "....###....",
        "....###....",
        "....###....",
        "....###....",
        "....###....",
        "....###....",
        "....###....",
    ],
    "R": [
        "#########..",
        "##########.",
        "###########",
        "###.....###",
        "###.....###",
        "###########",
        "##########.",
        "#########..",
        "###..###...",
        "###...###..",
        "###...###..",
        "###....###.",
        "###.....###",
    ],
    "A": [
        ".....###.....",
        ".....###.....",
        "....#####....",
        "....#####....",
        "...###.###...",
        "...###.###...",
        "..###...###..",
        "..###...###..",
        "..#########..",
        ".###########.",
        ".###########.",
        "###.......###",
        "###.......###",
    ],
    "L": [
        "###.......",
        "###.......",
        "###.......",
        "###.......",
        "###.......",
        "###.......",
        "###.......",
        "###.......",
        "###.......",
        "###.......",
        "##########",
        "##########",
        "##########",
    ],
    "Y": [
        "###.......###",
        "###.......###",
        ".###.....###.",
        "..###...###..",
        "..###...###..",
        "...###.###...",
        "....#####....",
        ".....###.....",
        ".....###.....",
        ".....###.....",
        ".....###.....",
        ".....###.....",
        ".....###.....",
    ],
    "O": [
        "..########..",
        ".##########.",
        "############",
        "###......###",
        "###......###",
        "###......###",
        "###......###",
        "###......###",
        "###......###",
        "###......###",
        "############",
        ".##########.",
        "..########..",
    ],
}

TEXTE_X = BX + BL + 11      # colonne où commence le texte
TEXTE_Y = BY + 21           # ligne du haut de « CENTRALE »
ESPACE_LETTRES = 2
ESPACE_LIGNES = 4
HAUTEUR_LETTRE = 13


def placer_lettres():
    """Renvoie la liste (lettre, x, y) des 12 lettres, dans l'ordre d'apparition."""
    places = []
    y = TEXTE_Y
    for mot in ("CENTRALE", "LYON"):
        x = TEXTE_X
        for lettre in mot:
            places.append((lettre, x, y))
            x += len(LETTRES[lettre][0]) + ESPACE_LETTRES
        y += HAUTEUR_LETTRE + ESPACE_LIGNES
    return places


PLACES_LETTRES = placer_lettres()
FIN_TEXTE_X = max(x + len(LETTRES[lettre][0]) for lettre, x, _ in PLACES_LETTRES)


def verifier_dessins():
    """Arrête le script si un dessin a une ligne trop courte ou trop longue."""
    dessins = [("LION_CORPS", LION_CORPS, 45), ("PATTES_A", PATTES_A, 45),
               ("ABEILLE_AILES_OUVERTES", ABEILLE_AILES_OUVERTES, 11),
               ("ABEILLE_AILES_FERMEES", ABEILLE_AILES_FERMEES, 11)]
    dessins += [(f"QUEUES[{nom}]", lignes, 10) for nom, lignes in QUEUES.items()]
    for nom, lignes, largeur in dessins:
        for i, ligne in enumerate(lignes):
            assert len(ligne) == largeur, f"{nom}, ligne {i} : {len(ligne)} cases au lieu de {largeur}"
    for lettre, lignes in LETTRES.items():
        assert len(lignes) == HAUTEUR_LETTRE, f"lettre {lettre} : {len(lignes)} lignes"
        for i, ligne in enumerate(lignes):
            assert len(ligne) == len(lignes[0]), f"lettre {lettre}, ligne {i} : largeur différente"
    assert FIN_TEXTE_X <= LARGEUR - 6, "le texte dépasse de la grille"


# --------------------------------------------------------------------------
# De la grille (gros pixels) à l'image réelle (pixels du GIF)
# --------------------------------------------------------------------------
# Les noms qui finissent par _G désignent des tableaux à la taille réelle.

G = ECHELLE
HG, LG = HAUTEUR * G, LARGEUR * G
YG, XG = np.mgrid[0:HG, 0:LG]        # ligne et colonne de chaque pixel réel


def agrandir(tableau):
    """Passe de la grille à la taille réelle : chaque case devient un carré G x G."""
    return np.repeat(np.repeat(tableau, G, axis=0), G, axis=1)


def sur_grille(tableau_blason, vide=False):
    """Pose un tableau du blason (72 x 55) à sa place dans la grille entière."""
    grille = np.full((HAUTEUR, LARGEUR), vide, dtype=tableau_blason.dtype)
    grille[BY:BY + BH, BX:BX + BL] = tableau_blason
    return grille


def masque_dessin(lignes, x0, y0, signe="#"):
    """Transforme un dessin en masque (True là où il y a le signe), dans la grille."""
    masque = np.zeros((HAUTEUR, LARGEUR), dtype=bool)
    for j, ligne in enumerate(lignes):
        for i, case in enumerate(ligne):
            if case == signe and 0 <= x0 + i < LARGEUR and 0 <= y0 + j < HAUTEUR:
                masque[y0 + j, x0 + i] = True
    return masque


def decaler(masque_g, dx, dy):
    """Déplace un masque de dx, dy pixels réels. Ce qui sort de l'image est perdu."""
    if dx == 0 and dy == 0:
        return masque_g
    resultat = np.zeros_like(masque_g)
    h, l = masque_g.shape
    x0, x1 = max(0, -dx), min(l, l - dx)
    y0, y1 = max(0, -dy), min(h, h - dy)
    resultat[y0 + dy:y1 + dy, x0 + dx:x1 + dx] = masque_g[y0:y1, x0:x1]
    return resultat


# Trame de fondu (matrice de Bayer 4 x 4) : pour afficher une forme « à 50 % »,
# on n'allume qu'une case sur deux, selon un motif régulier. TRAME_G donne à
# chaque pixel un rang de 0 à 15 ; au niveau k, on montre les rangs < k.
BAYER = np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]])
TRAME_G = BAYER[(YG // G) % 4, (XG // G) % 4]

# Les zones du blason, à la taille réelle
FORME_G = agrandir(sur_grille(FORME))
CONTOUR_G = agrandir(sur_grille(CONTOUR))
ZONE_BANDE_G = agrandir(sur_grille(INTERIEUR & (_ys <= BAS_BANDE)))     # bande rouge
ZONE_BAS_G = agrandir(sur_grille(INTERIEUR & (_ys > BAS_BANDE)))        # champ blanc
TRAIT_G = agrandir(sur_grille(INTERIEUR & (_ys > BAS_BANDE) & (_xs == AXE)))
ZONE_ABEILLES_G = agrandir(sur_grille(INTERIEUR & (_ys > BAS_BANDE) & (_xs < AXE)))
ZONE_ENGRENAGES = sur_grille(INTERIEUR & (_ys > BAS_BANDE) & (_xs > AXE))


def ordre_du_contour():
    """Donne à chaque case du contour son rang de tracé, de 0 (haut) à 1 (pointe)."""
    angle = np.abs(np.arctan2(_xs - AXE, -(_ys - 36.0)))   # 0 en haut, pi en bas
    rangs = np.full((BH, BL), 9.0)                          # 9 = jamais tracé
    tries = np.sort(angle[CONTOUR])
    rangs[CONTOUR] = np.searchsorted(tries, angle[CONTOUR], side="right") / CONTOUR.sum()
    return rangs


ORDRE_G = agrandir(sur_grille(ordre_du_contour(), vide=9.0))

# Les dessins, transformés une fois pour toutes en masques à la taille réelle
LION_G = {
    queue: agrandir(masque_dessin(lignes_lion(queue), BX + LION_X, BY + LION_Y)) & ZONE_BANDE_G
    for queue in QUEUES
}
ABEILLES_G = [
    {
        etat: (agrandir(masque_dessin(dessin, BX + ax, BY + ay, "#")),    # corps rouge
               agrandir(masque_dessin(dessin, BX + ax, BY + ay, "o")))    # ailes roses
        for etat, dessin in (("ouvertes", ABEILLE_AILES_OUVERTES), ("fermees", ABEILLE_AILES_FERMEES))
    }
    for ax, ay in ABEILLES
]
LETTRES_G = [agrandir(masque_dessin(LETTRES[lettre], x, y)) for lettre, x, y in PLACES_LETTRES]

# --------------------------------------------------------------------------
# Le déroulé de l'animation (durées en nombre d'images, 1 image = 30 ms)
# --------------------------------------------------------------------------

T_PAUSE = 206       # logo complet. La 1re image du GIF est donc le logo entier.
T_SORTIE = 22       # le logo s'estompe
T_POINT = 12        # il ne reste qu'un point doré, en haut du blason
T_CONSTRUIT = 168   # le logo se reconstruit, puis un reflet le traverse

D_SORTIE = T_PAUSE
D_POINT = D_SORTIE + T_SORTIE
D_CONSTRUIT = D_POINT + T_POINT
NB_IMAGES = D_CONSTRUIT + T_CONSTRUIT

# Pendant la construction, chaque élément a un (début, durée), comptés en images
# depuis le début de la construction. Les éléments se chevauchent exprès.
C_CONTOUR = (0, 30)
C_BANDE = (22, 24)
C_CHAMP = (38, 26)
C_LION = (54, 34)
C_ENGRENAGE = (72, 24)      # + 6 images de retard par engrenage
C_ABEILLE = (74, 18)        # + 6 images de retard par abeille
C_LETTRE = (88, 16)         # + 3 images de retard par lettre
C_REFLET = (126, 30)
C_ETINCELLES = ((136, 20), (144, 20))

IMAGES_PAR_DENT = 24        # un engrenage avance d'une dent en 24 images

# Les ailes (cycle de 8 images) et les engrenages doivent retrouver leur position
# de départ quand le GIF reboucle.
assert NB_IMAGES % 8 == 0 and NB_IMAGES % IMAGES_PAR_DENT == 0, f"NB_IMAGES = {NB_IMAGES}"


def part(t, debut, duree):
    """Avancement d'un élément : 0 avant son début, 1 après sa fin."""
    return min(1.0, max(0.0, (t - debut) / duree))


def doux(p):
    """Démarre lentement, accélère, puis ralentit (p et le résultat entre 0 et 1)."""
    return p * p * (3 - 2 * p)


def freine(p):
    """Démarre vite et se pose lentement."""
    return 1 - (1 - p) ** 3


def queue_du_lion(n):
    """Pendant la pause, le lion balance deux fois la queue, lentement."""
    positions = {"H": "haute", "M": "milieu", "B": "basse"}
    for debut, suite in ((30, "HMBMHMBMH"), (150, "HMBMH")):
        i = (n - debut) // 6
        if n >= debut and i < len(suite):
            return positions[suite[i]]
    return "haute"


# --------------------------------------------------------------------------
# Outils de dessin
# --------------------------------------------------------------------------


def masque_engrenage(cx, cy, rayon, dents, angle, anneau, balayage):
    """Un engrenage dans la grille : un cercle, des dents, un anneau au centre.

    balayage : part du tour déjà tracée (0 à 1), en partant du haut.
    """
    masque = np.zeros((HAUTEUR, LARGEUR), dtype=bool)
    pas = 2 * math.pi / dents          # angle entre deux dents
    portee = int(rayon) + 3
    for y in range(cy - portee, cy + portee + 1):
        for x in range(cx - portee, cx + portee + 1):
            distance = math.hypot(x - cx, y - cy)
            plein = abs(distance - rayon) <= 0.5
            if rayon + 0.5 < distance <= rayon + 1.5:
                ecart = (math.atan2(y - cy, x - cx) - angle) % pas
                ecart = min(ecart, pas - ecart)
                plein = ecart * distance <= 0.7
            if anneau and abs(distance - anneau) <= 0.5:
                plein = True
            if plein and balayage < 1:
                tour = math.atan2(x - cx, cy - y) % (2 * math.pi)   # 0 en haut
                plein = tour <= balayage * 2 * math.pi
            if plein:
                masque[BY + y, BX + x] = True
    return masque & ZONE_ENGRENAGES


def poser_reflet(image, position, zone_g=None):
    """Bande de lumière en biais. Elle éclaircit le rouge et le texte qu'elle croise."""
    d = XG + (HG - YG) * 0.5 - position            # distance au bord de la bande
    coeur = (d >= 0) & (d < 10)
    bord = ((d >= -8) & (d < 0)) | ((d >= 10) & (d < 18))
    voile = (((d >= -16) & (d < -8)) | ((d >= 18) & (d < 26))) & (TRAME_G < 8)
    filet = (d >= 36) & (d < 40)                   # second trait, plus fin
    rouge, texte = image == ROUGE, image == TEXTE
    if zone_g is not None:
        rouge, texte = rouge & zone_g, texte & zone_g
    image[rouge & (bord | voile | filet)] = REFLET
    image[rouge & coeur] = REFLET_FORT
    image[texte & (coeur | bord)] = REFLET_TEXTE


def poser_etincelle(image, x, y, taille):
    """Étoile dorée à quatre branches, en gros pixels. taille de 0 (rien) à 4."""
    cases = [(0, 0)] if taille >= 1 else []
    for d in range(1, taille):
        cases += [(d, 0), (-d, 0), (0, d), (0, -d)]
    if taille >= 4:
        cases += [(1, 1), (1, -1), (-1, 1), (-1, -1)]
    for dx, dy in cases:
        image[(y + dy) * G:(y + dy + 1) * G, (x + dx) * G:(x + dx + 1) * G] = OR


# --------------------------------------------------------------------------
# Une image de l'animation
# --------------------------------------------------------------------------


def dessiner_image(n):
    """Renvoie l'image numéro n : un tableau HG x LG de numéros de couleur."""
    image = np.zeros((HG, LG), dtype=np.uint8)
    graine_g = CONTOUR_G & (ORDRE_G <= 0.02)       # les cases d'où part le tracé
    if D_POINT <= n < D_CONSTRUIT:
        image[graine_g] = OR                       # il ne reste que le point doré
        return image

    fini = n < D_POINT                # pause et sortie : tout est en place
    t = n - D_CONSTRUIT               # temps écoulé depuis le début de la construction

    def avance(debut_duree, retard=0):
        debut, duree = debut_duree
        return 1.0 if fini else part(t, debut + retard, duree)

    # 1. Le contour se trace depuis le haut, des deux côtés, derrière une pointe dorée
    p = doux(avance(C_CONTOUR))
    image[CONTOUR_G & (ORDRE_G <= p)] = ROUGE
    if p < 1:
        image[CONTOUR_G & (ORDRE_G <= max(p, 0.02)) & (ORDRE_G > p - 0.04)] = OR

    # 2. La bande rouge descend, avec un liseré clair sur son bord
    p = freine(avance(C_BANDE))
    bord = BY * G + p * (BAS_BANDE + 1) * G
    image[ZONE_BANDE_G & (YG < bord)] = ROUGE
    if 0 < p < 1:
        image[ZONE_BANDE_G & (YG < bord) & (YG >= bord - G)] = REFLET

    # 3. Le champ blanc et le trait vertical descendent à leur tour
    p = doux(avance(C_CHAMP))
    bord = (BY + BAS_BANDE + 1) * G + p * (BH - BAS_BANDE - 1) * G
    image[ZONE_BAS_G & (YG < bord)] = BLANC
    image[TRAIT_G & (YG < bord)] = ROUGE

    # 4. Le lion est révélé de la queue à la tête, derrière un trait de lumière
    p = doux(avance(C_LION))
    bord = (BX - 4) * G + p * (BL + 8) * G
    lion_g = LION_G[queue_du_lion(n) if n < T_PAUSE else "haute"]
    if 0 < p < 1:
        image[ZONE_BANDE_G & (XG >= bord + 2 * G) & (XG < bord + 4 * G) & (TRAME_G < 8)] = REFLET
        image[ZONE_BANDE_G & (XG >= bord + G) & (XG < bord + 2 * G)] = REFLET
        image[ZONE_BANDE_G & (XG >= bord) & (XG < bord + G)] = REFLET_FORT
    image[lion_g & (XG < bord + G)] = BLANC

    # 5. Les engrenages se tracent en tournant, puis continuent de tourner lentement
    for i, (cx, cy, rayon, dents, sens, anneau) in enumerate(ENGRENAGES):
        p = freine(avance(C_ENGRENAGE, retard=6 * i))
        if p <= 0:
            continue
        angle = sens * (2 * math.pi / dents) * (n / IMAGES_PAR_DENT)
        if sens < 0:
            angle += math.pi / dents
        image[agrandir(masque_engrenage(cx, cy, rayon, dents, angle, anneau, p))] = ROUGE

    # 6. Les abeilles apparaissent en fondu, en montant, puis flottent sur place
    for i, etats in enumerate(ABEILLES_G):
        p = freine(avance(C_ABEILLE, retard=6 * i))
        if p <= 0:
            continue
        flotte = round(2 * math.sin(2 * math.pi * (5 * n / NB_IMAGES + i / 3)))   # -2 à 2 pixels
        dy = round((1 - p) * 10) + flotte
        corps_g, ailes_g = etats["ouvertes" if (n // 4 + i) % 2 == 0 else "fermees"]
        visible = ZONE_ABEILLES_G & (TRAME_G < round(p * 16))
        image[decaler(ailes_g, 0, dy) & visible] = AILE
        image[decaler(corps_g, 0, dy) & visible] = ROUGE

    # 7. Les lettres montent une à une en fondu et se posent en douceur
    for i, lettre_g in enumerate(LETTRES_G):
        p = avance(C_LETTRE, retard=3 * i)
        if p <= 0:
            continue
        dy = round((1 - freine(p)) * 14)
        niveau = round(min(1.0, p / 0.6) * 16)
        image[decaler(lettre_g, 0, dy) & (TRAME_G < niveau)] = TEXTE

    # 8. Fin de la construction : un reflet traverse tout le logo, puis deux étincelles
    if not fini:
        p = part(t, *C_REFLET)
        if 0 < p < 1:
            poser_reflet(image, -60 + doux(p) * (LG + HG / 2 + 120))
        coins = ((BX + BL + 3, BY + 2), (FIN_TEXTE_X + 3, TEXTE_Y - 5))
        for (debut, duree), (x, y) in zip(C_ETINCELLES, coins):
            p = part(t, debut, duree)
            if 0 < p < 1:
                poser_etincelle(image, x, y, round(math.sin(math.pi * p) * 4))

    # 9. Au milieu de la pause : un reflet discret, sur le blason seulement
    if n < T_PAUSE:
        p = part(n, 96, 28)
        if 0 < p < 1:
            poser_reflet(image, -30 + doux(p) * 500, zone_g=FORME_G)

    # 10. La sortie : le logo s'estompe en fondu tramé, il reste le point doré
    if D_SORTIE <= n < D_POINT:
        p = (n - D_SORTIE + 1) / T_SORTIE
        niveau = round((1 - doux(p)) * 16)
        image[TRAME_G >= niveau] = VIDE
        image[graine_g] = OR if niveau <= 4 else ROUGE

    return image


# --------------------------------------------------------------------------
# Écriture des GIF
# --------------------------------------------------------------------------


def vers_image_pillow(image, palette):
    """Transforme le tableau de numéros de couleur en image à palette."""
    resultat = Image.frombytes("P", (LG, HG), image.tobytes())
    couleurs = []
    for numero in range(len(palette)):
        couleurs.extend(palette[numero])
    resultat.putpalette(couleurs)
    return resultat


def toutes_les_images():
    """Calcule l'animation une fois. Renvoie (images, durées en millisecondes).

    Deux images de suite identiques : on n'en garde qu'une, affichée plus longtemps.
    """
    images, durees = [], []
    for n in range(NB_IMAGES):
        image = dessiner_image(n)
        # Pillow écrit un fichier abîmé si une image est entièrement transparente
        # (constaté le 26/11/2026 avec Pillow 12.3.0). On l'interdit donc ici.
        assert (image != VIDE).any(), f"image {n} entièrement vide"
        if images and np.array_equal(image, images[-1]):
            durees[-1] += DUREE_IMAGE_MS
        else:
            images.append(image)
            durees.append(DUREE_IMAGE_MS)
    return images, durees


def ecrire_gif(chemin, images, durees, palette):
    pages = [vers_image_pillow(image, palette) for image in images]
    pages[0].save(
        chemin,
        save_all=True,
        append_images=pages[1:],
        duration=durees,     # une durée par image, en millisecondes
        loop=0,              # 0 = boucle sans fin
        transparency=VIDE,   # la couleur n° 0 est transparente
        disposal=2,          # on efface l'image avant de dessiner la suivante
        optimize=False,
    )


def main():
    verifier_dessins()
    dossier = Path(__file__).resolve().parent.parent / "assets"
    dossier.mkdir(exist_ok=True)
    images, durees = toutes_les_images()
    for nom, palette in PALETTES.items():
        chemin = dossier / f"centrale-lyon-pixel-{nom}.gif"
        ecrire_gif(chemin, images, durees, palette)
        print(f"{chemin.name} : {len(images)} images, {sum(durees) / 1000:.2f} s, "
              f"{chemin.stat().st_size / 1024:.0f} Ko")


if __name__ == "__main__":
    main()
