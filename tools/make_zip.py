"""Cree une archive du code du projet, prete a etre envoyee sur Colab.

On n'archive QUE le code. Les donnees (plusieurs centaines de Mo), les poids de
modeles et l'environnement virtuel sont exclus : Colab regenere les donnees en
quelques minutes depuis Lichess, et reinstalle les dependances tout seul.
Resultat : une archive de quelques dizaines de kilo-octets au lieu de plusieurs
gigaoctets.

    python tools/make_zip.py
"""

from __future__ import annotations

import zipfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT = PROJECT_ROOT / "chess-bot-v1-pour-colab.zip"

#: Dossiers entierement exclus.
EXCLUDED_DIRS = {
    ".git", ".venv", "venv", "__pycache__", ".pytest_cache", ".idea", ".vscode",
    "data", "checkpoints", "bin", "POUR RAJAA",
}

#: Extensions exclues (fichiers lourds ou regenerables).
EXCLUDED_SUFFIXES = {".pt", ".pth", ".npz", ".zst", ".pgn", ".zip", ".html"}


def should_include(path: Path) -> bool:
    if any(part in EXCLUDED_DIRS for part in path.relative_to(PROJECT_ROOT).parts):
        return False
    return path.suffix.lower() not in EXCLUDED_SUFFIXES


def main() -> None:
    files = [
        path
        for path in PROJECT_ROOT.rglob("*")
        if path.is_file() and path != OUTPUT and should_include(path)
    ]

    with zipfile.ZipFile(OUTPUT, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            # Le prefixe "chess-bot-v1/" fait que l'archive se decompresse dans
            # un dossier propre, ce qu'attend le notebook.
            archive.write(path, Path("chess-bot-v1") / path.relative_to(PROJECT_ROOT))

    size_kb = OUTPUT.stat().st_size / 1024
    print(f"Archive creee : {OUTPUT.name}  ({size_kb:.0f} Ko, {len(files)} fichiers)")
    print(f"Emplacement   : {OUTPUT}")
    print()
    print("Envoyez ce fichier dans la cellule 'Option B' du notebook Colab.")


if __name__ == "__main__":
    main()
