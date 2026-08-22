"""Convertit un fichier Markdown en une page HTML autonome et lisible.

Pourquoi ce script existe
-------------------------
Le guide du projet est ecrit en Markdown (.md), un format texte pratique a
editer mais moche a lire pour quelqu'un qui n'a pas d'editeur adapte. Ce script
produit un fichier .html UNIQUE, sans aucune dependance externe : on peut
l'envoyer par WhatsApp ou par mail, le destinataire double-clique, ca s'ouvre
dans son navigateur. Rien a installer, aucun compte.

Usage
-----
    python tools/build_html.py GUIDE-PROJET.md
    python tools/build_html.py GUIDE-PROJET.md -o docs/guide.html
"""

from __future__ import annotations

import argparse
import html
import re
from pathlib import Path

# ---------------------------------------------------------------------------
# Feuille de style
#
# Identite visuelle : encre profonde et laiton vieilli (les materiaux d'une
# pendule d'echecs et d'un manuel d'ouvertures), serif pour les titres comme
# dans la litterature echiqueenne, sans-serif pour le corps de texte.
# ---------------------------------------------------------------------------
STYLESHEET = """
:root {
  color-scheme: light dark;

  --ground:      #f7f4ee;   /* parchemin, legerement chaud */
  --surface:     #fffdf9;
  --surface-alt: #efe9df;
  --ink:         #23201c;
  --ink-soft:    #5b544a;
  --ink-faint:   #8b8175;
  --rule:        #ded5c7;
  --brass:       #9a6b1f;   /* accent : laiton */
  --brass-soft:  #c9a35a;
  --deep:        #1d3049;   /* secondaire : encre bleue */

  --measure: 70ch;
  --step--1: 0.86rem;
  --step-0:  1.0625rem;
  --step-1:  1.32rem;
  --step-2:  1.72rem;
  --step-3:  2.3rem;
  --step-4:  3rem;
}

@media (prefers-color-scheme: dark) {
  :root {
    --ground:      #16181b;
    --surface:     #1c1f23;
    --surface-alt: #24282d;
    --ink:         #e7e3db;
    --ink-soft:    #a9a49a;
    --ink-faint:   #77726a;
    --rule:        #33383e;
    --brass:       #d8a94e;
    --brass-soft:  #8d6c2e;
    --deep:        #8fb3d9;
  }
}

:root[data-theme="light"] {
  --ground: #f7f4ee; --surface: #fffdf9; --surface-alt: #efe9df;
  --ink: #23201c; --ink-soft: #5b544a; --ink-faint: #8b8175;
  --rule: #ded5c7; --brass: #9a6b1f; --brass-soft: #c9a35a; --deep: #1d3049;
}
:root[data-theme="dark"] {
  --ground: #16181b; --surface: #1c1f23; --surface-alt: #24282d;
  --ink: #e7e3db; --ink-soft: #a9a49a; --ink-faint: #77726a;
  --rule: #33383e; --brass: #d8a94e; --brass-soft: #8d6c2e; --deep: #8fb3d9;
}

* { box-sizing: border-box; }

body {
  margin: 0;
  background: var(--ground);
  color: var(--ink);
  font-family: "Segoe UI", system-ui, -apple-system, "Helvetica Neue", sans-serif;
  font-size: var(--step-0);
  line-height: 1.68;
  -webkit-font-smoothing: antialiased;
}

.page {
  max-width: var(--measure);
  margin: 0 auto;
  padding: clamp(2rem, 6vw, 5rem) clamp(1.1rem, 4vw, 2rem) 6rem;
  display: flex;
  flex-direction: column;
  gap: 1.35rem;
}

/* --- Titres : serif, comme un manuel d'echecs --- */
h1, h2, h3, h4 {
  font-family: "Iowan Old Style", "Palatino Linotype", Palatino, Georgia, serif;
  font-weight: 600;
  line-height: 1.18;
  text-wrap: balance;
  margin: 0;
}

h1 {
  font-size: var(--step-4);
  letter-spacing: -0.022em;
  margin-bottom: 0.2rem;
}

h2 {
  font-size: var(--step-2);
  margin-top: 3.2rem;
  padding-top: 1.5rem;
  border-top: 1px solid var(--rule);
  letter-spacing: -0.012em;
}

h3 {
  font-size: var(--step-1);
  margin-top: 1.9rem;
  color: var(--deep);
}

h4 {
  font-size: var(--step-0);
  margin-top: 1.4rem;
  text-transform: uppercase;
  letter-spacing: 0.09em;
  font-family: inherit;
  font-weight: 700;
  color: var(--ink-soft);
}

p { margin: 0; }

a {
  color: var(--brass);
  text-decoration-thickness: 1px;
  text-underline-offset: 2px;
}
a:hover { color: var(--ink); }
a:focus-visible {
  outline: 2px solid var(--brass);
  outline-offset: 3px;
  border-radius: 2px;
}

strong { font-weight: 650; color: var(--ink); }

ul, ol {
  margin: 0;
  padding-left: 1.35rem;
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}
li::marker { color: var(--brass-soft); }

hr {
  border: 0;
  height: 1px;
  background: var(--rule);
  margin: 2rem 0;
}

/* --- Code --- */
code {
  font-family: ui-monospace, "Cascadia Mono", "SF Mono", Consolas, monospace;
  font-size: 0.88em;
  background: var(--surface-alt);
  padding: 0.12em 0.38em;
  border-radius: 3px;
}

pre {
  margin: 0;
  background: var(--surface);
  border: 1px solid var(--rule);
  border-left: 3px solid var(--brass-soft);
  border-radius: 4px;
  padding: 1rem 1.15rem;
  overflow-x: auto;
  line-height: 1.55;
}
pre code {
  background: none;
  padding: 0;
  font-size: var(--step--1);
  color: var(--ink-soft);
}

/* --- Citations : les points a retenir --- */
blockquote {
  margin: 0;
  padding: 0.9rem 1.2rem;
  background: var(--surface);
  border-left: 3px solid var(--brass);
  border-radius: 0 4px 4px 0;
  color: var(--ink-soft);
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
}

/* --- Tableaux --- */
.table-wrap { overflow-x: auto; }
table {
  border-collapse: collapse;
  width: 100%;
  font-size: var(--step--1);
  font-variant-numeric: tabular-nums;
}
th, td {
  text-align: left;
  padding: 0.55rem 0.75rem;
  border-bottom: 1px solid var(--rule);
  vertical-align: top;
}
th {
  font-weight: 700;
  font-size: 0.78rem;
  text-transform: uppercase;
  letter-spacing: 0.07em;
  color: var(--ink-faint);
  border-bottom: 1.5px solid var(--rule);
}
tbody tr:hover { background: var(--surface); }

/* --- Cases a cocher du planning --- */
.task { list-style: none; }
ul:has(> .task) { padding-left: 0.2rem; }
.task input {
  margin-right: 0.55rem;
  accent-color: var(--brass);
}

/* --- Sommaire --- */
.toc {
  background: var(--surface);
  border: 1px solid var(--rule);
  border-radius: 5px;
  padding: 1.3rem 1.5rem;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}
.toc h2 {
  margin: 0;
  padding: 0;
  border: 0;
  font-size: 0.78rem;
  font-family: inherit;
  text-transform: uppercase;
  letter-spacing: 0.11em;
  color: var(--ink-faint);
}
.toc ol {
  list-style: none;
  padding: 0;
  counter-reset: toc;
  gap: 0.3rem;
}
.toc li { counter-increment: toc; }
.toc li::before {
  content: counter(toc, decimal-leading-zero);
  color: var(--brass-soft);
  font-size: 0.78rem;
  font-variant-numeric: tabular-nums;
  margin-right: 0.7rem;
}
.toc a { text-decoration: none; color: var(--ink); }
.toc a:hover { color: var(--brass); text-decoration: underline; }

.doc-meta {
  font-size: var(--step--1);
  color: var(--ink-faint);
  letter-spacing: 0.02em;
}

@media print {
  body { background: #fff; }
  /* Le contenu s'enchaine normalement d'une page a l'autre : on evite
     seulement qu'un titre reste seul en bas de page, ou qu'un tableau/bloc
     soit coupe au milieu. Forcer une page neuve a CHAQUE section (comme une
     precedente version de cette feuille de style le faisait) laissait des
     pages presque vides des qu'une section etait courte. */
  h1, h2, h3, h4 { break-after: avoid; }
  table, blockquote, .toc, pre { break-inside: avoid; }
}
"""

PAGE_TEMPLATE = """<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>{stylesheet}</style>
</head>
<body>
<main class="page">
{body}
</main>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# Conversion du Markdown en HTML
# ---------------------------------------------------------------------------

def _slugify(text: str) -> str:
    """Transforme un titre en identifiant utilisable dans une ancre #lien."""
    slug = re.sub(r"[^\w\s-]", "", text.lower())
    return re.sub(r"[\s_]+", "-", slug).strip("-") or "section"


def _inline(text: str) -> str:
    """Applique le formatage en ligne : code, gras, italique, liens.

    Le code entre backticks est mis de cote AVANT tout le reste, sinon un `*`
    a l'interieur d'un extrait de code serait interprete comme de l'italique.
    """
    placeholders: list[str] = []

    def stash(match: re.Match[str]) -> str:
        placeholders.append(f"<code>{html.escape(match.group(1))}</code>")
        return f"\x00{len(placeholders) - 1}\x00"

    text = re.sub(r"`([^`]+)`", stash, text)
    text = html.escape(text)

    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<![\w*])\*([^*\n]+)\*(?![\w*])", r"<em>\1</em>", text)

    return re.sub(r"\x00(\d+)\x00", lambda m: placeholders[int(m.group(1))], text)


def _render_table(rows: list[str]) -> str:
    """Convertit un tableau Markdown (la ligne de tirets est ignoree)."""
    def cells(line: str) -> list[str]:
        return [c.strip() for c in line.strip().strip("|").split("|")]

    header = cells(rows[0])
    body = [cells(row) for row in rows[2:]]

    out = ['<div class="table-wrap"><table>', "<thead><tr>"]
    out += [f"<th>{_inline(c)}</th>" for c in header]
    out.append("</tr></thead><tbody>")
    for row in body:
        out.append("<tr>" + "".join(f"<td>{_inline(c)}</td>" for c in row) + "</tr>")
    out.append("</tbody></table></div>")
    return "".join(out)


def markdown_to_html(source: str) -> tuple[str, str, list[tuple[str, str]]]:
    """Convertit du Markdown. Renvoie (titre, corps_html, sommaire)."""
    lines = source.splitlines()
    out: list[str] = []
    toc: list[tuple[str, str]] = []
    title = "Document"

    index = 0
    while index < len(lines):
        line = lines[index]
        stripped = line.strip()

        # --- Bloc de code ---
        if stripped.startswith("```"):
            index += 1
            block: list[str] = []
            while index < len(lines) and not lines[index].strip().startswith("```"):
                block.append(lines[index])
                index += 1
            index += 1
            out.append(f"<pre><code>{html.escape(chr(10).join(block))}</code></pre>")
            continue

        # --- Ligne vide ---
        if not stripped:
            index += 1
            continue

        # --- Separateur ---
        if re.fullmatch(r"-{3,}|\*{3,}", stripped):
            out.append("<hr>")
            index += 1
            continue

        # --- Titres ---
        heading = re.match(r"^(#{1,4})\s+(.*)$", stripped)
        if heading:
            level = len(heading.group(1))
            text = heading.group(2)
            if level == 1:
                title = re.sub(r"[*`]", "", text)
                out.append(f"<h1>{_inline(text)}</h1>")
            else:
                slug = _slugify(text)
                if level == 2:
                    toc.append((slug, re.sub(r"[*`]", "", text)))
                out.append(f'<h{level} id="{slug}">{_inline(text)}</h{level}>')
            index += 1
            continue

        # --- Tableau ---
        if stripped.startswith("|") and index + 1 < len(lines) and set(
            lines[index + 1].strip()
        ) <= set("|-: "):
            table_rows = []
            while index < len(lines) and lines[index].strip().startswith("|"):
                table_rows.append(lines[index])
                index += 1
            out.append(_render_table(table_rows))
            continue

        # --- Citation ---
        if stripped.startswith(">"):
            quote: list[str] = []
            while index < len(lines) and lines[index].strip().startswith(">"):
                quote.append(lines[index].strip().lstrip(">").strip())
                index += 1
            paragraphs = [p for p in "\n".join(quote).split("\n\n") if p.strip()]
            inner = "".join(f"<p>{_inline(p)}</p>" for p in paragraphs)
            out.append(f"<blockquote>{inner}</blockquote>")
            continue

        # --- Listes ---
        bullet = re.match(r"^\s*([-*]|\d+\.)\s+(.*)$", line)
        if bullet:
            ordered = bool(re.match(r"^\s*\d+\.", line))
            items: list[str] = []
            while index < len(lines):
                item = re.match(r"^\s*([-*]|\d+\.)\s+(.*)$", lines[index])
                if not item:
                    break
                content = item.group(2)
                checkbox = re.match(r"^\[( |x|X)\]\s*(.*)$", content)
                if checkbox:
                    checked = " checked" if checkbox.group(1).lower() == "x" else ""
                    items.append(
                        f'<li class="task"><input type="checkbox" disabled{checked}>'
                        f"{_inline(checkbox.group(2))}</li>"
                    )
                else:
                    items.append(f"<li>{_inline(content)}</li>")
                index += 1
            tag = "ol" if ordered else "ul"
            out.append(f"<{tag}>{''.join(items)}</{tag}>")
            continue

        # --- Paragraphe ---
        # Une ligne qui se termine par deux espaces ou plus est un saut de
        # ligne force en Markdown (comme un <br>) : on le garde AVANT de
        # rogner les espaces, sinon deux lignes voulues distinctes (ex. les
        # lignes d'un bloc auteur) fusionnent silencieusement en une seule.
        paragraph: list[str] = []
        while index < len(lines) and lines[index].strip() and not re.match(
            r"^\s*(#{1,4}\s|[-*]\s|\d+\.\s|>|\||```|-{3,}$)", lines[index]
        ):
            raw = lines[index]
            hard_break = raw.rstrip("\n").endswith("  ")
            paragraph.append((raw.strip(), hard_break))
            index += 1
        if paragraph:
            pieces = []
            for i, (text, hard_break) in enumerate(paragraph):
                pieces.append(_inline(text))
                if i < len(paragraph) - 1:
                    pieces.append("<br>" if hard_break else " ")
            out.append(f"<p>{''.join(pieces)}</p>")
        else:
            index += 1

    return title, "\n".join(out), toc


def build(source_path: Path, output_path: Path) -> Path:
    title, body, toc = markdown_to_html(source_path.read_text(encoding="utf-8"))

    if toc:
        entries = "".join(f'<li><a href="#{slug}">{html.escape(text)}</a></li>' for slug, text in toc)
        toc_html = f'<nav class="toc"><h2>Sommaire</h2><ol>{entries}</ol></nav>'
        # On insere le sommaire juste apres le titre principal.
        parts = body.split("\n", 1)
        body = parts[0] + "\n" + toc_html + "\n" + (parts[1] if len(parts) > 1 else "")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        PAGE_TEMPLATE.format(title=html.escape(title), stylesheet=STYLESHEET, body=body),
        encoding="utf-8",
    )
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Markdown -> page HTML autonome.")
    parser.add_argument("source", help="fichier .md a convertir")
    parser.add_argument("-o", "--output", default=None, help="fichier .html de sortie")
    args = parser.parse_args()

    source = Path(args.source)
    output = Path(args.output) if args.output else source.with_suffix(".html")
    result = build(source, output)
    size_kb = result.stat().st_size / 1024
    print(f"Page ecrite : {result}  ({size_kb:.0f} Ko)")
    print("Envoyez ce fichier tel quel : il s'ouvre dans n'importe quel navigateur.")


if __name__ == "__main__":
    main()
