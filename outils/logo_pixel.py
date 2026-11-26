"""Logo de Centrale Lyon en pixel art, animé, pour le profil GitHub.

Script écrit avec Claude Code (Anthropic), modèle Claude Fable 5.2, le 25/11/2026.
Le logo appartient à l'École Centrale de Lyon. Ce fichier n'en fait qu'un dessin
en pixels pour un profil d'élève.

Lancer :
    python outils/logo_pixel.py

Le script écrit deux GIF dans assets/ :
    centrale-lyon-pixel-clair.gif    (texte rouge, pour le thème clair de GitHub)
    centrale-lyon-pixel-sombre.gif   (texte blanc, pour le thème sombre)

Principe : chaque image est une grille de petits entiers (un entier = une couleur
de la palette). On dessine dans cette grille à basse résolution, puis on grossit
chaque case en un carré de ECHELLE x ECHELLE pixels.
"""

import math
import random
from pathlib import Path

import numpy as np
from PIL import Image

# --------------------------------------------------------------------------
# Réglages généraux
# --------------------------------------------------------------------------

LARGEUR, HAUTEUR = 186, 88   # taille de la grille, en « gros pixels »
ECHELLE = 4                  # 1 gros pixel = 4 x 4 pixels dans le GIF
DUREE_IMAGE_MS = 80          # 80 ms par image = 12,5 images par seconde

# Numéros de couleur dans la palette
VIDE, ROUGE, BLANC, TEXTE, REFLET, REFLET_TEXTE, AILE = 0, 1, 2, 3, 4, 5, 6

ROUGE_CENTRALE = (178, 33, 51)   # mesuré sur le logo fourni

PALETTES = {
    "clair": {
        VIDE: (0, 0, 0),                 # jamais affichée : couleur transparente
        ROUGE: ROUGE_CENTRALE,
        BLANC: (255, 255, 255),
        TEXTE: ROUGE_CENTRALE,
        REFLET: (236, 120, 134),
        REFLET_TEXTE: (236, 120, 134),
        AILE: (232, 150, 160),
    },
    "sombre": {
        VIDE: (0, 0, 0),
        ROUGE: ROUGE_CENTRALE,
        BLANC: (255, 255, 255),
        TEXTE: (255, 255, 255),
        REFLET: (236, 120, 134),
        REFLET_TEXTE: (255, 176, 186),
        AILE: (232, 150, 160),
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
ZONE_BANDE = INTERIEUR & (_ys <= BAS_BANDE)                      # où marche le lion
ZONE_ABEILLES = INTERIEUR & (_ys > BAS_BANDE) & (_xs < AXE)      # quart bas gauche
ZONE_ENGRENAGES = INTERIEUR & (_ys > BAS_BANDE) & (_xs > AXE)    # quart bas droit
# Ordre d'apparition du contour : 0 en haut au milieu, 1 à la pointe du bas
ORDRE_CONTOUR = np.abs(np.arctan2(_xs - AXE, -(_ys - 36.0))) / math.pi
# La case du haut du blason, d'où part le tracé du contour (ligne, colonne dans la grille).
# Elle reste toujours allumée : voir la remarque dans ecrire_gif.
GRAINE = (BY, BX + AXE)

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

# Pattes rapprochées : la deuxième image de la marche
PATTES_B = [
    ".......#######.#####.......###########.......",
    ".........#####..####........####.####........",
    "..........###....###........###...###........",
    "..........##.....##.........##....##.........",
    "..........##.....##.........##....##.........",
    "..........###....###........###...###........",
]

# Queue baissée : remplace les 10 premières colonnes des lignes 9 à 12 du corps
QUEUE_BASSE = [
    ".......###",
    "......##..",
    "...###....",
    "###.......",
]


def lion(pose="A", queue_basse=False):
    """Renvoie (lignes du dessin, décalage vertical) pour une pose du lion."""
    corps = list(LION_CORPS)
    if queue_basse:
        for i, debut in enumerate(QUEUE_BASSE):
            corps[9 + i] = debut + corps[9 + i][10:]
    if pose == "A":
        return corps + PATTES_A, 0
    # Pose B : le corps monte d'une case, les pattes s'allongent d'autant
    return corps + [corps[-1]] + PATTES_B, -1


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
    for nom, lignes, largeur in [
        ("LION_CORPS", LION_CORPS, 45), ("PATTES_A", PATTES_A, 45), ("PATTES_B", PATTES_B, 45),
        ("QUEUE_BASSE", QUEUE_BASSE, 10),
        ("ABEILLE_AILES_OUVERTES", ABEILLE_AILES_OUVERTES, 11),
        ("ABEILLE_AILES_FERMEES", ABEILLE_AILES_FERMEES, 11),
    ]:
        for i, ligne in enumerate(lignes):
            assert len(ligne) == largeur, f"{nom}, ligne {i} : {len(ligne)} cases au lieu de {largeur}"
    for lettre, lignes in LETTRES.items():
        assert len(lignes) == HAUTEUR_LETTRE, f"lettre {lettre} : {len(lignes)} lignes"
        for i, ligne in enumerate(lignes):
            assert len(ligne) == len(lignes[0]), f"lettre {lettre}, ligne {i} : largeur différente"
    assert FIN_TEXTE_X <= LARGEUR - 6, "le texte dépasse de la grille"


# --------------------------------------------------------------------------
# Le déroulé de l'animation (durées en nombre d'images)
# --------------------------------------------------------------------------

T_PAUSE = 83      # logo complet. La 1re image du GIF est donc le logo entier.
T_EFFACE = 10     # le logo se défait case par case
T_VIDE = 4        # il ne reste qu'une case rouge, en haut du blason
T_CONTOUR = 14    # le contour du blason se trace
T_REMPLI = 12     # le blason se remplit de haut en bas
T_LION = 27       # le lion entre en marchant
T_BAS = 22        # les abeilles arrivent, les engrenages apparaissent
T_TEXTE = 30      # les lettres tombent une à une
T_REFLET = 22     # un reflet traverse le logo

D_EFFACE = T_PAUSE
D_VIDE = D_EFFACE + T_EFFACE
D_CONTOUR = D_VIDE + T_VIDE
D_REMPLI = D_CONTOUR + T_CONTOUR
D_LION = D_REMPLI + T_REMPLI
D_BAS = D_LION + T_LION
D_TEXTE = D_BAS + T_BAS
D_REFLET = D_TEXTE + T_TEXTE
NB_IMAGES = D_REFLET + T_REFLET

# Le nombre d'images doit être un multiple de 8 : les ailes et les engrenages
# reviennent alors exactement à leur position de départ quand le GIF reboucle.
assert NB_IMAGES % 8 == 0, f"NB_IMAGES = {NB_IMAGES}, il faut un multiple de 8"

# Tirage au sort fixe (graine 7) : l'ordre dans lequel les cases s'effacent
_hasard = random.Random(7)
ORDRE_EFFACEMENT = np.array(
    [[_hasard.random() for _ in range(LARGEUR)] for _ in range(HAUTEUR)]
)

# --------------------------------------------------------------------------
# Outils de dessin
# --------------------------------------------------------------------------


def poser_dessin(grille, lignes, x0, y0, couleur, zone=None):
    """Recopie un dessin dans la grille, à partir de (x0, y0).

    '#' = case de la couleur demandée, 'o' = case rose (aile), '.' = rien.

    zone : masque du blason (72 x 55). Si elle est donnée, x0 et y0 sont des
    coordonnées dans le blason, et rien n'est dessiné hors de la zone.
    """
    for j, ligne in enumerate(lignes):
        for i, case in enumerate(ligne):
            if case == ".":
                continue
            teinte = AILE if case == "o" else couleur
            x, y = x0 + i, y0 + j
            if zone is not None:
                if not (0 <= x < BL and 0 <= y < BH and zone[y, x]):
                    continue
                x, y = x + BX, y + BY
            if 0 <= x < LARGEUR and 0 <= y < HAUTEUR:
                grille[y, x] = teinte


def poser_engrenage(grille, cx, cy, rayon, dents, angle, anneau):
    """Dessine un engrenage : un cercle, des dents autour, un anneau au centre."""
    pas = 2 * math.pi / dents          # angle entre deux dents
    portee = int(rayon) + 3
    for y in range(cy - portee, cy + portee + 1):
        for x in range(cx - portee, cx + portee + 1):
            if not (0 <= x < BL and 0 <= y < BH and ZONE_ENGRENAGES[y, x]):
                continue
            distance = math.hypot(x - cx, y - cy)
            plein = abs(distance - rayon) <= 0.5
            if rayon + 0.5 < distance <= rayon + 1.5:
                ecart = (math.atan2(y - cy, x - cx) - angle) % pas
                ecart = min(ecart, pas - ecart)
                plein = ecart * distance <= 0.7
            if anneau and abs(distance - anneau) <= 0.5:
                plein = True
            if plein:
                grille[y + BY, x + BX] = ROUGE


def poser_etincelle(grille, x, y, taille):
    """Petite croix qui grandit puis rétrécit. taille 0 = rien."""
    if taille <= 0:
        return
    for d in range(-(taille - 1), taille):
        grille[y, x + d] = ROUGE
        grille[y + d, x] = ROUGE
    if taille == 3:
        grille[y, x] = VIDE


def avancement(n, debut, duree):
    """0 avant le début, 1 après la fin, entre les deux pendant."""
    return min(1.0, max(0.0, (n - debut) / duree))


# --------------------------------------------------------------------------
# Une image de l'animation
# --------------------------------------------------------------------------


def dessiner_image(n):
    """Renvoie la grille (HAUTEUR x LARGEUR) de l'image numéro n."""
    grille = np.full((HAUTEUR, LARGEUR), VIDE, dtype=np.uint8)
    logo_complet = n < D_VIDE          # pendant la pause et l'effacement
    if D_VIDE <= n < D_CONTOUR:
        grille[GRAINE] = ROUGE         # une seule case : le départ du tracé
        return grille

    blason = grille[BY:BY + BH, BX:BX + BL]   # une « fenêtre » sur la grille

    # 1. Contour du blason, qui se trace depuis le haut
    trace = 1.0 if logo_complet else (n - D_CONTOUR + 1) / T_CONTOUR
    blason[CONTOUR & (ORDRE_CONTOUR <= trace)] = ROUGE

    # 2. Remplissage de haut en bas
    lignes_remplies = BH if logo_complet else int(avancement(n, D_REMPLI, T_REMPLI - 1) * BH)
    rempli = INTERIEUR & (_ys < lignes_remplies)
    blason[rempli & (_ys <= BAS_BANDE)] = ROUGE
    blason[rempli & (_ys > BAS_BANDE)] = BLANC
    blason[rempli & (_ys > BAS_BANDE) & (_xs == AXE)] = ROUGE     # trait vertical

    # 3. Le lion
    t = n - D_LION
    if logo_complet or t >= 0:
        marche = (not logo_complet) and t < 26
        decalage = -(52 - 2 * t) if marche else 0
        pose = "B" if marche and (t // 3) % 2 == 1 else "A"
        if marche:
            queue_basse = (t // 6) % 2 == 1
        else:
            # deux coups de queue pendant la pause
            queue_basse = logo_complet and (24 <= n < 44 or 58 <= n < 68) and (n // 5) % 2 == 0
        lignes, dy = lion(pose, queue_basse)
        poser_dessin(grille, lignes, LION_X + decalage, LION_Y + dy, BLANC, zone=ZONE_BANDE)

    # 4. Les abeilles : elles entrent par la gauche, puis battent des ailes sur place
    for i, (ax, ay) in enumerate(ABEILLES):
        depart = D_BAS - 4 + 3 * i     # elles partent un peu avant, cachées par le bord
        if not logo_complet and n < depart:
            continue
        reste = 0.0 if logo_complet else (1 - avancement(n, depart, 12)) ** 2
        ailes = ABEILLE_AILES_OUVERTES if (n // 2 + i) % 2 == 0 else ABEILLE_AILES_FERMEES
        flotte = round(math.sin(2 * math.pi * (n / NB_IMAGES * 7 + i / 3)))   # -1, 0 ou 1
        x = ax - round(reste * 24)
        y = ay + flotte + round(reste * (8 if i == 2 else -4))
        poser_dessin(grille, ailes, x, y, ROUGE, zone=ZONE_ABEILLES)

    # 5. Les engrenages : ils grossissent d'un coup, puis tournent
    for i, (cx, cy, rayon, dents, sens, anneau) in enumerate(ENGRENAGES):
        t = n - (D_BAS + 4 + 4 * i)
        if not logo_complet and t < 0:
            continue
        grossissement = 1.0 if logo_complet or t >= 3 else (0.45, 0.8, 1.15)[t]
        # une dent avance d'un cran toutes les 8 images
        angle = sens * (2 * math.pi / dents) * (n / 8) + (math.pi / dents if sens < 0 else 0)
        poser_engrenage(grille, cx, cy, rayon * grossissement, dents, angle,
                        anneau if grossissement == 1.0 else 0)

    # 6. Les lettres : chacune tombe, dépasse d'une case, puis se pose
    chute = (-6, -3, -1, 1, 0)
    for i, (lettre, x, y) in enumerate(PLACES_LETTRES):
        t = n - (D_TEXTE + 2 * i)
        if not logo_complet and t < 0:
            continue
        dy = 0 if logo_complet or t >= len(chute) else chute[t]
        poser_dessin(grille, LETTRES[lettre], x, y + dy, TEXTE)

    # 7. Le reflet : deux bandes en biais qui traversent de gauche à droite
    if n >= D_REFLET:
        t = n - D_REFLET
        ys, xs = np.mgrid[0:HAUTEUR, 0:LARGEUR]
        position = xs + (HAUTEUR - ys) * 0.5 - (-24 + 13 * t)
        bande = ((position >= 0) & (position < 6)) | ((position >= 9) & (position < 11))
        grille[bande & (grille == ROUGE)] = REFLET
        grille[bande & (grille == TEXTE)] = REFLET_TEXTE
        # deux étincelles à la fin du reflet
        tailles = (1, 2, 3, 3, 2, 1)
        for retard, (ex, ey) in ((10, (BX + BL + 3, BY + 2)), (14, (FIN_TEXTE_X + 3, TEXTE_Y - 5))):
            if 0 <= t - retard < len(tailles):
                poser_etincelle(grille, ex, ey, tailles[t - retard])

    # 8. L'effacement : de plus en plus de cases disparaissent, au hasard
    if D_EFFACE <= n < D_VIDE:
        part_effacee = (n - D_EFFACE + 1) / T_EFFACE
        grille[ORDRE_EFFACEMENT < part_effacee] = VIDE
        grille[GRAINE] = ROUGE

    return grille


# --------------------------------------------------------------------------
# Écriture des GIF
# --------------------------------------------------------------------------


def grille_vers_image(grille, palette):
    """Grossit la grille et la transforme en image à palette."""
    grande = np.repeat(np.repeat(grille, ECHELLE, axis=0), ECHELLE, axis=1)
    image = Image.fromarray(grande, mode="P")
    couleurs = []
    for numero in range(len(palette)):
        couleurs.extend(palette[numero])
    image.putpalette(couleurs)
    return image


def ecrire_gif(chemin, palette):
    """Écrit le GIF et renvoie le nombre d'images réellement enregistrées."""
    # Deux images de suite identiques : on n'en garde qu'une, affichée plus longtemps.
    grilles, durees = [], []
    for n in range(NB_IMAGES):
        grille = dessiner_image(n)
        # Pillow écrit un fichier abîmé si une image est entièrement transparente
        # (constaté le 26/11/2026 avec Pillow 12.3.0). On l'interdit donc ici.
        assert (grille != VIDE).any(), f"image {n} entièrement vide"
        if grilles and np.array_equal(grille, grilles[-1]):
            durees[-1] += DUREE_IMAGE_MS
        else:
            grilles.append(grille)
            durees.append(DUREE_IMAGE_MS)

    images = [grille_vers_image(grille, palette) for grille in grilles]
    images[0].save(
        chemin,
        save_all=True,
        append_images=images[1:],
        duration=durees,     # une durée par image, en millisecondes
        loop=0,              # 0 = boucle sans fin
        transparency=VIDE,   # la couleur n° 0 est transparente
        disposal=2,          # on efface l'image avant de dessiner la suivante
        optimize=False,
    )
    return len(images)


def main():
    verifier_dessins()
    dossier = Path(__file__).resolve().parent.parent / "assets"
    dossier.mkdir(exist_ok=True)
    for nom, palette in PALETTES.items():
        chemin = dossier / f"centrale-lyon-pixel-{nom}.gif"
        nb = ecrire_gif(chemin, palette)
        duree_s = NB_IMAGES * DUREE_IMAGE_MS / 1000
        print(f"{chemin.name} : {nb} images, {duree_s:.1f} s, {chemin.stat().st_size / 1024:.0f} Ko")


if __name__ == "__main__":
    main()
