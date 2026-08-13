"""Genere la presentation de soutenance (.pptx) et le guide oral (.md).

Deux livrables produits d'un coup :

  Soutenance_Chess_Bot_v1.pptx  — le diaporama, avec le texte a dire dans les
                                   NOTES de chaque diapo (menu Affichage > Commentaires
                                   dans PowerPoint).
  GUIDE-ORAL.md                 — le meme script oral, sous forme de document a
                                   imprimer et garder en main pendant l'oral.

    python tools/make_slides.py
"""

from __future__ import annotations

from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.util import Emu, Pt

ROOT = Path(__file__).resolve().parents[1]
PPTX_OUT = ROOT / "POUR RAJAA" / "Soutenance_Chess_Bot_v1.pptx"
ORAL_OUT = ROOT / "GUIDE-ORAL.md"

# Palette coherente avec l'application : blanc, encre, rose poudre.
INK = RGBColor(0x1C, 0x1A, 0x1B)
SOFT = RGBColor(0x5D, 0x55, 0x59)
ROSE = RGBColor(0xB8, 0x53, 0x6E)
LIGHT = RGBColor(0xF1, 0xEC, 0xEE)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)

# Dimensions 16:9.
SLIDE_W = Emu(12192000)
SLIDE_H = Emu(6858000)

FONT = "Segoe UI"

# ---------------------------------------------------------------------------
# Contenu : chaque diapo = titre, sous-titre, puces, et script oral.
# ---------------------------------------------------------------------------

SLIDES = [
    {
        "title": "Chess Bot v1",
        "subtitle": "Un Transformer qui joue aux echecs sans recherche",
        "bullets": [
            "Projet de fin de Bachelor",
            "[Prenom NOM] & [Prenom NOM]",
            "[Etablissement] — 24 aout 2026",
        ],
        "cover": True,
        "oral": (
            "Bonjour. Nous allons vous presenter Chess Bot v1, un projet d'intelligence "
            "artificielle qui apprend a un reseau de neurones a jouer aux echecs. La "
            "particularite : notre bot ne calcule aucune variante, il choisit son coup "
            "directement en regardant la position. Je suis [X], voici [Y], et on se "
            "repartit la presentation."
        ),
    },
    {
        "title": "La question de depart",
        "subtitle": "",
        "bullets": [
            "Les moteurs classiques (Deep Blue, Stockfish) EXPLORENT des millions de positions.",
            "Notre bot, lui, ne cherche pas : il repond a l'instinct, comme un humain en blitz.",
            "Question : un Transformer peut-il jouer correctement SANS recherche ?",
        ],
        "oral": (
            "Depuis Deep Blue en 1997, les ordinateurs battent l'humain aux echecs en "
            "explorant des millions de positions a chaque coup — c'est de la force brute. "
            "Nous, on pose une question differente, inspiree d'un article de DeepMind de "
            "2024 : est-ce qu'un reseau de neurones peut jouer correctement sans jamais "
            "explorer l'arbre des coups, juste en reconnaissant les bonnes positions ? "
            "C'est tout l'enjeu du projet."
        ),
    },
    {
        "title": "Contexte : les echecs et l'IA",
        "subtitle": "Un demi-siecle d'approches",
        "bullets": [
            "1997 — Deep Blue bat Kasparov : recherche alpha-beta massive.",
            "2017 — AlphaZero : reseau de neurones + recherche (MCTS).",
            "2020+ — Stockfish : alpha-beta + petit reseau d'evaluation.",
            "2024 — DeepMind : un Transformer SEUL, sans recherche. Notre reference.",
        ],
        "oral": (
            "Petit tour d'horizon. Toutes les grandes approches ont un point commun : "
            "elles cherchent. Deep Blue, AlphaZero, Stockfish, tous explorent des coups "
            "futurs. En 2024, DeepMind montre qu'un Transformer seul, sans aucune "
            "recherche, peut atteindre un niveau de grand maitre. C'est l'article qui "
            "nous sert de reference, et qu'on adapte a notre echelle."
        ),
    },
    {
        "title": "Notre pari",
        "subtitle": "Une version reduite et assumee",
        "bullets": [
            "DeepMind : 270 millions de parametres, 10 millions de parties, des TPU.",
            "Nous : 6,9 millions de parametres, 1 million de positions, un GPU gratuit.",
            "Objectif realiste : mesurer honnetement ce qu'un petit modele peut apprendre.",
        ],
        "oral": (
            "Attention, on ne refait pas DeepMind : eux avaient des moyens colossaux. "
            "Nous, on fait une version 40 fois plus petite, avec un GPU gratuit et "
            "quelques semaines. Notre objectif n'est pas de battre Stockfish, mais de "
            "construire toute la chaine proprement et de mesurer honnetement ce qu'un "
            "petit modele arrive a apprendre. La rigueur compte plus que la performance."
        ),
    },
    {
        "title": "Vue d'ensemble",
        "subtitle": "De la partie brute au bot qui joue",
        "bullets": [
            "1. Donnees : parties Lichess -> 1 million de positions.",
            "2. Encodage : chaque position -> 68 nombres.",
            "3. Modele : le Transformer choisit un coup parmi 1968.",
            "4. Evaluation : matchs contre Stockfish -> Elo.",
        ],
        "oral": (
            "Voici le plan de la chaine, en quatre etapes. On recupere des parties de "
            "joueurs forts, on transforme chaque position en nombres, on entraine le "
            "Transformer a choisir un coup, et enfin on mesure son niveau en le faisant "
            "jouer contre Stockfish. Je vais detailler chaque etape."
        ),
    },
    {
        "title": "Etape 1 — Les donnees",
        "subtitle": "Apprendre de bons joueurs",
        "bullets": [
            "Source : base ouverte Lichess (parties reelles).",
            "Filtres : joueurs > 2000 Elo, pas de bullet, parties terminees.",
            "Resultat : 1 000 000 de positions en ~5 minutes (lecture en flux).",
            "Principe : le bot imite les coups d'un joueur fort (clonage comportemental).",
        ],
        "oral": (
            "On part de la base publique de Lichess, qui contient des millions de parties "
            "reelles. On ne garde que les parties de joueurs forts, au-dessus de 2000 Elo, "
            "pour apprendre de bonnes decisions. On extrait un million de positions en "
            "cinq minutes grace a une lecture optimisee. L'idee, c'est le clonage "
            "comportemental : le modele apprend a imiter le coup joue par l'expert."
        ),
    },
    {
        "title": "Etape 2 — Encoder une position",
        "subtitle": "Une position = 68 nombres",
        "bullets": [
            "64 cases + trait + roques + prise en passant = 68 tokens.",
            "Chaque case est un mot ; l'attention relie les cases eloignees.",
            "Astuce : on retourne l'echiquier pour toujours jouer les blancs.",
            "-> le modele apprend 2 fois plus vite.",
        ],
        "oral": (
            "Un reseau ne comprend que des nombres. On transforme donc chaque position en "
            "68 nombres : le contenu des 64 cases, plus quelques informations comme le "
            "trait et les roques. On traite l'echiquier comme une phrase de 68 mots, ce "
            "qui permet au mecanisme d'attention du Transformer de relier une case a "
            "l'autre bout du plateau. Detail malin : on retourne toujours l'echiquier du "
            "point de vue du joueur au trait, donc le modele n'a qu'une seule vue a "
            "apprendre, et il apprend deux fois plus vite."
        ),
    },
    {
        "title": "Etape 3 — Le modele",
        "subtitle": "Un Transformer encodeur",
        "bullets": [
            "8 couches d'attention, 6,86 millions de parametres.",
            "Entree : 68 tokens. Sortie : un score pour chacun des 1968 coups possibles.",
            "C'est une classification : ranger une position parmi 1968 categories.",
        ],
        "oral": (
            "Le coeur du projet : le Transformer. C'est le meme type de reseau que ceux "
            "qui traitent le langage, mais adapte aux echecs. Il a huit couches et presque "
            "sept millions de parametres. Il prend nos 68 nombres en entree et sort un "
            "score pour chacun des 1968 coups concevables. Formellement, c'est un probleme "
            "de classification tres classique : ranger une position dans la bonne "
            "categorie de coup."
        ),
    },
    {
        "title": "Choisir un coup legal",
        "subtitle": "Le bot ne triche jamais",
        "bullets": [
            "Le reseau note les 1968 coups possibles.",
            "On met a -infini tous les coups ILLEGAUX dans la position.",
            "On garde le meilleur des coups restants.",
            "=> impossible de jouer un coup illegal, par construction.",
        ],
        "oral": (
            "Une question classique du jury : et si le bot propose un coup impossible ? "
            "Reponse : c'est impossible par construction. Le reseau note les 1968 coups, "
            "mais avant de choisir, on elimine tous ceux qui sont illegaux dans la "
            "position en leur donnant un score de moins l'infini. Le bot ne peut donc "
            "structurellement jamais tricher."
        ),
    },
    {
        "title": "L'entrainement",
        "subtitle": "4 epoques sur 1 million de positions (GPU gratuit)",
        "bullets": [
            "La perte descend de 7,6 (hasard) a 3,1.",
            "Exactitude top-1 : 22,7 % — top-5 : 51,7 %.",
            "Pas de surapprentissage (validation suivie separement).",
            "[Inserer ici la figure des courbes]",
        ],
        "oral": (
            "On entraine le modele sur GPU gratuit. La courbe de perte descend "
            "regulierement : le modele apprend. A la fin, il retrouve le coup exact du "
            "joueur dans 22,7 % des cas, et le bon coup est dans ses cinq premieres "
            "propositions une fois sur deux. Point important a comprendre : 22 %, ce n'est "
            "pas un mauvais score. Dans beaucoup de positions plusieurs coups se valent, "
            "donc le modele peut avoir raison en proposant autre chose que l'humain. "
            "Cette exactitude mesure l'imitation, pas la force reelle."
        ),
    },
    {
        "title": "Resultat 1 — Il a appris les ouvertures",
        "subtitle": "Dans la position de depart, le reseau propose :",
        "bullets": [
            "d3 (32 %) · Cc3 (17 %) · Cf3 (14 %) · d4 (10 %) · c4 (8 %)",
            "Ce sont de vrais coups d'ouverture : developpement, centre.",
            "Aucune regle ne lui a ete enseignee — il a appris en observant.",
        ],
        "oral": (
            "Premier resultat, et c'est le plus parlant. Si on demande au reseau ce qu'il "
            "propose au tout premier coup, il repond : sortir les cavaliers, occuper le "
            "centre. Ce sont exactement les principes d'ouverture qu'on apprend a un "
            "debutant. Or on ne lui a JAMAIS explique une seule regle : il a deduit ces "
            "principes tout seul, juste en regardant des parties. Ca, c'est la preuve "
            "qu'il a vraiment appris quelque chose."
        ),
    },
    {
        "title": "Resultat 2 — Le niveau mesure",
        "subtitle": "60 parties par adversaire, intervalles de confiance a 95 %",
        "table": [
            ["Adversaire", "Score", "Elo estime"],
            ["Aleatoire (~250)", "47,5 %", "233 [146 ; 320]"],
            ["Glouton (~600)", "9,2 %", "202 [54 ; 349]"],
            ["Minimax-2 (~1100)", "1,7 %", "392"],
            ["Stockfish 1320", "3,3 %", "< 1320 (perd tout)"],
        ],
        "oral": (
            "Deuxieme resultat : le niveau reel, mesure en parties. On fait jouer le bot "
            "contre une echelle d'adversaires de force croissante, 60 parties chacun, avec "
            "des intervalles de confiance. Le verdict est honnete : notre bot tourne autour "
            "de 250 a 300 Elo, un niveau de tout debutant. Face a Stockfish, meme a son "
            "reglage le plus faible, il perd toutes ses parties. On donne toujours "
            "l'intervalle de confiance, jamais un chiffre seul."
        ),
    },
    {
        "title": "Analyse : forces et faiblesses",
        "subtitle": "",
        "bullets": [
            "+ Il connait les principes d'ouverture.",
            "+ Il ne joue jamais de coup illegal.",
            "- Il joue passivement : beaucoup de nulles, il ne conclut pas.",
            "- Sans recherche, il rate la tactique et les finales.",
        ],
        "oral": (
            "Qu'est-ce que ca nous apprend ? Le bot sait commencer une partie, mais il ne "
            "sait pas la finir : il tourne en rond et fait beaucoup de nulles, meme contre "
            "l'aleatoire. C'est logique : sans recherche, il joue a l'intuition et ne "
            "verifie jamais un calcul. C'est exactement la limite qu'on voulait etudier : "
            "la connaissance ne remplace pas totalement le calcul."
        ),
    },
    {
        "title": "L'application",
        "subtitle": "Jouer contre le bot, et voir dans sa tete",
        "bullets": [
            "On joue contre le Transformer dans le navigateur.",
            "Mode spectateur : deux bots s'affrontent, on regarde.",
            "A chaque coup : les probabilites du reseau s'affichent.",
            "[Demo en direct ici]",
        ],
        "oral": (
            "On a aussi developpe une application pour jouer contre le bot. Le plus "
            "interessant, c'est cette zone qui montre, a chaque coup, les probabilites qui "
            "sortent du reseau : on voit litteralement l'interieur du modele reflechir. "
            "Je vous fais une courte demonstration. (Lancer le mode spectateur : deux bots "
            "jouent, commenter les coups envisages.)"
        ),
    },
    {
        "title": "Limites et perspectives",
        "subtitle": "",
        "bullets": [
            "Passer a l'action-value (probabilite de gain de chaque coup), comme DeepMind.",
            "Annoter les donnees avec Stockfish : apprendre du meilleur coup, pas du coup humain.",
            "Ajouter une recherche legere guidee par le reseau.",
            "Entrainer plus longtemps (un abonnement GPU stable).",
        ],
        "oral": (
            "Avec plus de temps, on voit quatre pistes. Predire la probabilite de gagner "
            "de chaque coup plutot que d'imiter, comme DeepMind. Faire annoter nos donnees "
            "par Stockfish pour apprendre du meilleur coup. Ajouter une petite recherche "
            "guidee par le reseau, qui corrigerait la tactique. Et simplement entrainer "
            "plus longtemps, ce que les deconnexions du GPU gratuit nous ont empeche de "
            "faire."
        ),
    },
    {
        "title": "Gestion de projet",
        "subtitle": "Un binome, un depot Git",
        "bullets": [
            "[Prenom] : donnees, encodage, modele, entrainement.",
            "[Prenom] : moteur, baselines, evaluation, application.",
            "Commun : rapport, documentation, soutenance.",
            "Difficultes : debit des donnees, saturation de l'Elo, deconnexions Colab.",
        ],
        "oral": (
            "Cote organisation, on s'est reparti le travail en deux axes : [X] sur les "
            "donnees et le modele, [Y] sur l'evaluation et l'application, et on a tout "
            "versionne sur Git. On a rencontre de vraies difficultes techniques : la "
            "lecture des donnees trop lente qu'on a accelere par vingt, le calcul d'Elo "
            "qui saturait a 100 % de victoires qu'on a corrige avec la methode de Wilson, "
            "et les deconnexions de Colab qu'on a contournees en sauvegardant sur le Drive."
        ),
    },
    {
        "title": "Conclusion",
        "subtitle": "",
        "bullets": [
            "Un Transformer apprend a jouer sans recherche, juste en observant.",
            "Niveau modeste (~250 Elo), mais principes d'ouverture reels.",
            "Chaine complete, testee, reproductible, mesuree rigoureusement.",
            "L'essentiel : la difference entre connaissance et calcul.",
        ],
        "oral": (
            "Pour conclure : on a montre qu'un petit Transformer peut apprendre a jouer "
            "aux echecs sans aucune recherche, uniquement en observant des parties. Son "
            "niveau reste modeste, mais il acquiert de vrais principes, et surtout toute "
            "la demarche est rigoureuse et reproductible. Au fond, ce projet illustre la "
            "difference entre la connaissance, ce que le reseau a memorise, et le calcul, "
            "qu'on a volontairement retire. Merci de votre attention, nous sommes prets "
            "pour vos questions."
        ),
    },
    {
        "title": "Merci",
        "subtitle": "Questions ?",
        "bullets": [
            "github.com/naadjath/chess-bot-v1",
        ],
        "cover": True,
        "oral": (
            "Merci. (Garder en tete les reponses aux questions frequentes : pourquoi un "
            "Transformer plutot qu'un CNN, comment on garantit la fiabilite de l'Elo, "
            "est-ce qu'il peut jouer un coup illegal, qu'est-ce qui a ete le plus dur. "
            "Elles sont dans le guide du projet, partie 7.)"
        ),
    },
]


# ---------------------------------------------------------------------------
# Construction du .pptx
# ---------------------------------------------------------------------------

def _textbox(slide, left, top, width, height, anchor=MSO_ANCHOR.TOP):
    box = slide.shapes.add_textbox(left, top, width, height)
    tf = box.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    return tf


def _set(run, size, color, bold=False, italic=False):
    run.font.name = FONT
    run.font.size = Pt(size)
    run.font.color.rgb = color
    run.font.bold = bold
    run.font.italic = italic


def _bg(slide, color):
    fill = slide.background.fill
    fill.solid()
    fill.fore_color.rgb = color


def add_content_slide(prs, data):
    slide = prs.slides.add_slide(prs.slide_layouts[6])  # vierge
    _bg(slide, WHITE)

    # Barre d'accent rose a gauche du titre.
    bar = slide.shapes.add_shape(1, Emu(600000), Emu(560000), Emu(90000), Emu(620000))
    bar.fill.solid()
    bar.fill.fore_color.rgb = ROSE
    bar.line.fill.background()
    bar.shadow.inherit = False

    # Titre + sous-titre.
    tf = _textbox(slide, Emu(820000), Emu(500000), Emu(10500000), Emu(1100000))
    p = tf.paragraphs[0]
    _set(p.add_run(), 34, INK, bold=True)
    p.runs[0].text = data["title"]
    if data.get("subtitle"):
        p2 = tf.add_paragraph()
        _set(p2.add_run(), 17, ROSE, bold=True)
        p2.runs[0].text = data["subtitle"]

    # Corps : puces ou tableau.
    if data.get("table"):
        _add_table(slide, data["table"])
    else:
        _add_bullets(slide, data.get("bullets", []))

    _add_notes(slide, data["oral"])
    _add_footer(slide)
    return slide


def _add_bullets(slide, bullets):
    tf = _textbox(slide, Emu(820000), Emu(2000000), Emu(10600000), Emu(4200000))
    for i, text in enumerate(bullets):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.space_after = Pt(16)
        emphasis = text.startswith("[")
        dot = p.add_run()
        _set(dot, 20, ROSE, bold=True)
        dot.text = "•  "
        run = p.add_run()
        _set(run, 20, SOFT if emphasis else INK, italic=emphasis)
        run.text = text


def _add_table(slide, rows):
    n, m = len(rows), len(rows[0])
    table = slide.shapes.add_table(
        n, m, Emu(820000), Emu(2100000), Emu(10500000), Emu(3200000)
    ).table
    for c in range(m):
        for r in range(n):
            cell = table.cell(r, c)
            cell.fill.solid()
            cell.fill.fore_color.rgb = ROSE if r == 0 else (LIGHT if r % 2 else WHITE)
            para = cell.text_frame.paragraphs[0]
            run = para.add_run()
            run.text = rows[r][c]
            _set(run, 15, WHITE if r == 0 else INK, bold=(r == 0))
            para.alignment = PP_ALIGN.LEFT if c == 0 else PP_ALIGN.CENTER


def add_cover_slide(prs, data):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _bg(slide, INK)

    tf = _textbox(slide, Emu(800000), Emu(2300000), Emu(10600000), Emu(2400000), MSO_ANCHOR.MIDDLE)
    p = tf.paragraphs[0]
    _set(p.add_run(), 54, WHITE, bold=True)
    p.runs[0].text = data["title"]

    if data.get("subtitle"):
        p2 = tf.add_paragraph()
        p2.space_before = Pt(10)
        _set(p2.add_run(), 24, ROSE, bold=True)
        p2.runs[0].text = data["subtitle"]

    for line in data.get("bullets", []):
        pl = tf.add_paragraph()
        pl.space_before = Pt(6)
        _set(pl.add_run(), 16, RGBColor(0xC9, 0xC2, 0xC5))
        pl.runs[0].text = line

    _add_notes(slide, data["oral"])
    return slide


def _add_footer(slide):
    tf = _textbox(slide, Emu(820000), Emu(6350000), Emu(10500000), Emu(360000))
    r = tf.paragraphs[0].add_run()
    _set(r, 10, RGBColor(0xA0, 0x98, 0x9C))
    r.text = "Chess Bot v1 — un Transformer joue aux echecs sans recherche"


def _add_notes(slide, text):
    slide.notes_slide.notes_text_frame.text = "A DIRE :\n\n" + text


def build_pptx() -> None:
    prs = Presentation()
    prs.slide_width = SLIDE_W
    prs.slide_height = SLIDE_H

    for data in SLIDES:
        if data.get("cover"):
            add_cover_slide(prs, data)
        else:
            add_content_slide(prs, data)

    PPTX_OUT.parent.mkdir(parents=True, exist_ok=True)
    prs.save(PPTX_OUT)
    print(f"Diaporama ecrit : {PPTX_OUT}  ({len(SLIDES)} diapos)")


def build_oral_guide() -> None:
    lines = [
        "# Guide oral — soutenance Chess Bot v1",
        "",
        "*Ce qu'il faut dire pour chaque diapo. A imprimer et garder en main.*",
        "",
        "**Conseils generaux :**",
        "- Parlez lentement, respirez entre les diapos.",
        "- Ne lisez pas la diapo : elle est pour le jury, votre texte est ici.",
        "- Repetez a voix haute au moins 3 fois, en chronometrant (visez 12-15 min).",
        "- Repartissez-vous les diapos a deux, en alternance.",
        "",
        "---",
        "",
    ]
    for i, data in enumerate(SLIDES, 1):
        lines.append(f"## Diapo {i} — {data['title']}")
        if data.get("subtitle"):
            lines.append(f"*{data['subtitle']}*")
        lines.append("")
        lines.append("**A l'ecran :**")
        if data.get("table"):
            lines.append("*(tableau des resultats Elo)*")
        for b in data.get("bullets", []):
            lines.append(f"- {b}")
        lines.append("")
        lines.append("**A dire :**")
        lines.append(f"> {data['oral']}")
        lines.append("")
        lines.append("---")
        lines.append("")

    ORAL_OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"Guide oral ecrit : {ORAL_OUT}")


if __name__ == "__main__":
    build_pptx()
    build_oral_guide()
