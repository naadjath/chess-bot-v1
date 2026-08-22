"""Construit le dossier LIVRABLES, pret a etre rendu au professeur.

Ce dossier ne doit contenir QUE les livrables officiels, dans un format sobre
et lisible sans outil particulier (PDF). Aucun outil de travail personnel
(guide oral, brouillons, images sources) n'y figure : ceux-la restent a la
racine du projet.

Etapes :
  1. Convertit les documents Markdown en PDF (via une page HTML intermediaire
     et l'impression headless de Chrome).
  2. Copie le modele entraine, les parties PGN de la campagne d'evaluation,
     et une archive du code source.
  3. Copie le support de soutenance (.pptx). La conversion en PDF de celui-ci
     se fait a part, avec PowerPoint (voir README de ce script).

Prerequis : avoir lance au prealable
    python tools/make_slide_assets.py
    python tools/make_slides.py
et place le PDF de la soutenance dans LIVRABLES/6-Soutenance/Soutenance.pdf
(export PowerPoint : Fichier > Exporter > Creer un document PDF/XPS).

    python tools/build_livrables.py
"""

from __future__ import annotations

import shutil
import subprocess
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LIVRABLES = ROOT / "LIVRABLES"
BUILD_HTML = ROOT / "build" / "html_tmp"

CHROME_CANDIDATES = [
    Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
    Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
    Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"),
]

#: Dossiers/fichiers jamais inclus dans l'archive de code source : donnees et
#: poids regenerables, outils personnels, environnement local.
EXCLUDED_DIRS = {
    ".git", ".venv", "venv", "__pycache__", ".pytest_cache", ".idea", ".vscode",
    "data", "checkpoints", "bin", "POUR RAJAA", "LIVRABLES", "build",
}
EXCLUDED_FILES = {"GUIDE-ORAL.md", "Soutenance_Chess_Bot_v1.pptx"}
EXCLUDED_SUFFIXES = {".pt", ".pth", ".npz", ".zst", ".pgn", ".zip"}


def find_browser() -> str:
    for candidate in CHROME_CANDIDATES:
        if candidate.exists():
            return str(candidate)
    raise SystemExit("Ni Chrome ni Edge trouve : impossible de generer les PDF.")


def markdown_to_pdf(md_path: Path, pdf_path: Path, browser: str) -> None:
    BUILD_HTML.mkdir(parents=True, exist_ok=True)
    html_path = BUILD_HTML / (md_path.stem + ".html")
    subprocess.run(
        ["python", str(ROOT / "tools" / "build_html.py"), str(md_path), "-o", str(html_path)],
        check=True, cwd=ROOT,
    )
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            browser, "--headless", "--disable-gpu", "--no-pdf-header-footer",
            f"--print-to-pdf={pdf_path}", "--print-to-pdf-no-header",
            html_path.resolve().as_uri(),
        ],
        check=True,
    )
    print(f"PDF ecrit : {pdf_path}")


def should_include(path: Path) -> bool:
    if any(part in EXCLUDED_DIRS for part in path.relative_to(ROOT).parts):
        return False
    if path.name in EXCLUDED_FILES:
        return False
    return path.suffix.lower() not in EXCLUDED_SUFFIXES


def make_source_zip(output: Path) -> None:
    files = [p for p in ROOT.rglob("*") if p.is_file() and should_include(p)]
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            archive.write(path, Path("chess-bot-v1") / path.relative_to(ROOT))
    print(f"Archive ecrite : {output}  ({len(files)} fichiers)")


def main() -> None:
    # LIVRABLES est entierement reconstruit a chaque fois : seul le PDF final
    # doit y vivre, jamais de source .md (voir LISEZ-MOI-SOURCE.md a la racine).
    if LIVRABLES.exists():
        shutil.rmtree(LIVRABLES)
    LIVRABLES.mkdir()

    browser = find_browser()

    # 1. Application (code source)
    make_source_zip(LIVRABLES / "1-Application" / "code-source.zip")

    # 2. Modele entraine
    dest = LIVRABLES / "2-Modele-entraine"
    dest.mkdir(parents=True, exist_ok=True)
    shutil.copy(ROOT / "checkpoints" / "best.pt", dest / "best.pt")
    if (ROOT / "checkpoints" / "history.json").exists():
        shutil.copy(ROOT / "checkpoints" / "history.json", dest / "history.json")

    # 3. Evaluation Elo
    dest = LIVRABLES / "3-Evaluation-ELO"
    markdown_to_pdf(ROOT / "results" / "elo_report.md", dest / "Rapport-ELO.pdf", browser)
    pgn_dest = dest / "parties-PGN"
    pgn_dest.mkdir(parents=True, exist_ok=True)
    for pgn in (ROOT / "results" / "games").glob("*.pgn"):
        shutil.copy(pgn, pgn_dest / pgn.name)

    # 4. Rapport
    markdown_to_pdf(ROOT / "RAPPORT.md", LIVRABLES / "4-Rapport" / "Rapport.pdf", browser)

    # 5. Documentation (le README sert de documentation technique officielle)
    markdown_to_pdf(ROOT / "README.md", LIVRABLES / "5-Documentation" / "Documentation.pdf", browser)

    # 6. Soutenance : le pptx est copie (support de presentation), le PDF est
    # genere a part avec PowerPoint (voir tools/export_soutenance_pdf.ps1).
    dest = LIVRABLES / "6-Soutenance"
    dest.mkdir(parents=True, exist_ok=True)
    shutil.copy(ROOT / "Soutenance_Chess_Bot_v1.pptx", dest / "Soutenance.pptx")

    # LISEZ-MOI, en dernier pour qu'il decrive un dossier deja complet. Sa
    # source vit hors de LIVRABLES : seul le PDF y est livre.
    markdown_to_pdf(ROOT / "LISEZ-MOI-SOURCE.md", LIVRABLES / "LISEZ-MOI.pdf", browser)

    shutil.rmtree(BUILD_HTML, ignore_errors=True)
    print("\nLIVRABLES pret. Pensez a generer 6-Soutenance/Soutenance.pdf depuis PowerPoint.")


if __name__ == "__main__":
    main()
