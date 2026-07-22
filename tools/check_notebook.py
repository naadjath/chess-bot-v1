"""Verifie qu'un notebook est valide avant de l'ouvrir dans Colab.

Trois controles :
  - le JSON est bien forme et respecte le format nbformat ;
  - chaque cellule de code est du Python syntaxiquement correct (les lignes
    magiques `!` et `%`, propres a IPython, sont neutralisees avant l'analyse) ;
  - aucune continuation de ligne `\\` ne subsiste dans une commande shell : elles
    ne sont pas fiables dans les cellules Colab et cassent silencieusement la
    commande, qui s'execute alors tronquee.

    python tools/check_notebook.py notebooks/Entrainement_Colab.ipynb
"""

from __future__ import annotations

import ast
import json
import sys
from pathlib import Path

BACKSLASH = chr(92)


def check(path: Path) -> int:
    notebook = json.loads(path.read_text(encoding="utf-8"))
    problems = 0

    for index, cell in enumerate(notebook["cells"]):
        if cell["cell_type"] != "code":
            continue
        source = "".join(cell["source"])

        for line in source.split("\n"):
            if line.rstrip().endswith(BACKSLASH):
                problems += 1
                print(f"  cellule {index} : continuation de ligne -> {line.strip()[:60]}")

        neutralised = "\n".join(
            "pass" if line.strip().startswith(("!", "%")) else line
            for line in source.split("\n")
        )
        try:
            ast.parse(neutralised)
        except SyntaxError as error:
            problems += 1
            print(f"  cellule {index} : erreur de syntaxe ligne {error.lineno} — {error.msg}")

    code_cells = sum(1 for c in notebook["cells"] if c["cell_type"] == "code")
    print(f"{path.name} : {len(notebook['cells'])} cellules ({code_cells} de code)")
    print(f"nbformat {notebook['nbformat']} · accelerateur {notebook['metadata'].get('accelerator', 'aucun')}")
    print("Aucun probleme detecte." if problems == 0 else f"{problems} probleme(s).")
    return problems


if __name__ == "__main__":
    target = Path(sys.argv[1] if len(sys.argv) > 1 else "notebooks/Entrainement_Colab.ipynb")
    sys.exit(1 if check(target) else 0)
