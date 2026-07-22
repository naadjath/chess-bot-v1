"""L'interface web du jeu : une seule page HTML, autonome.

Pourquoi tout est dans un seul fichier Python
---------------------------------------------
On aurait pu utiliser Gradio, Streamlit ou React. On s'en passe volontairement :

  - zero installation supplementaire (le jury lance le projet sans galerer)
  - zero dependance externe au chargement (pas de CDN : ca marche hors ligne)
  - on maitrise entierement le rendu, donc on peut afficher ce qui nous
    interesse vraiment : les coups que le modele a envisages et leur probabilite

L'echiquier est dessine en CSS (une grille 8x8) avec les caracteres Unicode des
pieces d'echecs. Aucune image a telecharger.
"""

from __future__ import annotations

PAGE = r"""<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Chess Bot v1</title>
<style>
/* ---------------------------------------------------------------------------
   Identite visuelle
   L'echiquier reste strictement noir et blanc, dans les deux themes : c'est un
   echiquier, pas une decoration. Toute la couleur du projet tient dans un seul
   rose poudre, reserve aux textes d'accent, aux boutons et aux indications de
   jeu. Les gris ne sont pas neutres : ils tirent tres legerement vers ce rose,
   ce qui fait tenir l'ensemble.
--------------------------------------------------------------------------- */
:root {
  color-scheme: light dark;
  --ground:#faf8f9; --surface:#ffffff; --surface-alt:#f1ecee;
  --ink:#1c1a1b; --ink-soft:#5d5559; --ink-faint:#948a8e;
  --rule:#e4dcdf;
  --rose:#b8536e; --rose-soft:#e0a6b6; --rose-wash:#fbeff2; --on-rose:#ffffff;

  /* L'echiquier : blanc et noir, point. */
  --light-sq:#ffffff; --dark-sq:#1e1c1d;
  --hint:rgba(184,83,110,.55); --from:rgba(184,83,110,.28); --last:rgba(184,83,110,.16);
}
@media (prefers-color-scheme: dark) {
  :root {
    --ground:#131113; --surface:#1a181a; --surface-alt:#231f22;
    --ink:#ece7e9; --ink-soft:#aaa0a4; --ink-faint:#786e72;
    --rule:#332d31;
    --rose:#e79ab0; --rose-soft:#8a4f61; --rose-wash:#251a1e; --on-rose:#241418;

    --light-sq:#f2f0f1; --dark-sq:#141314;
    --hint:rgba(231,154,176,.6); --from:rgba(231,154,176,.3); --last:rgba(231,154,176,.18);
  }
}
:root[data-theme="light"]{--ground:#faf8f9;--surface:#ffffff;--surface-alt:#f1ecee;--ink:#1c1a1b;--ink-soft:#5d5559;--ink-faint:#948a8e;--rule:#e4dcdf;--rose:#b8536e;--rose-soft:#e0a6b6;--rose-wash:#fbeff2;--on-rose:#ffffff;--light-sq:#ffffff;--dark-sq:#1e1c1d;--hint:rgba(184,83,110,.55);--from:rgba(184,83,110,.28);--last:rgba(184,83,110,.16);}
:root[data-theme="dark"]{--ground:#131113;--surface:#1a181a;--surface-alt:#231f22;--ink:#ece7e9;--ink-soft:#aaa0a4;--ink-faint:#786e72;--rule:#332d31;--rose:#e79ab0;--rose-soft:#8a4f61;--rose-wash:#251a1e;--on-rose:#241418;--light-sq:#f2f0f1;--dark-sq:#141314;--hint:rgba(231,154,176,.6);--from:rgba(231,154,176,.3);--last:rgba(231,154,176,.18);}

*{box-sizing:border-box;}
body{
  margin:0; min-height:100vh; background:var(--ground); color:var(--ink);
  font-family:"Segoe UI",system-ui,-apple-system,sans-serif;
  display:flex; align-items:flex-start; justify-content:center;
  padding:clamp(1rem,4vw,3rem);
}
.app{display:flex; flex-wrap:wrap; gap:clamp(1.2rem,3vw,2.5rem); align-items:flex-start; max-width:1000px; width:100%;}

/* ---------- Echiquier ---------- */
.board-side{display:flex; flex-direction:column; gap:.75rem; flex:1 1 420px; min-width:320px;}
.board{
  display:grid; grid-template-columns:repeat(8,1fr); aspect-ratio:1;
  border:1px solid var(--rule); border-radius:5px; overflow:hidden;
  box-shadow:0 12px 32px -18px rgba(0,0,0,.55); user-select:none;
}
.sq{
  position:relative; display:grid; place-items:center;
  font-size:clamp(1.8rem,6.2vw,3.1rem); line-height:1; cursor:default;
  transition:background-color .12s ease;
}
.sq.light{background:var(--light-sq);} .sq.dark{background:var(--dark-sq);}
.sq.playable{cursor:pointer;}
.sq.last::after{content:"";position:absolute;inset:0;background:var(--last);}
.sq.selected::after{content:"";position:absolute;inset:0;background:var(--from);}
/* Les deux camps utilisent le meme glyphe PLEIN, differencies par la couleur de
   remplissage et un contour inverse. Sur un echiquier strictement noir et
   blanc, c'est le seul moyen qu'une piece blanche reste visible sur une case
   blanche (et inversement) — les glyphes Unicode "creux" disparaitraient. */
.sq .piece{position:relative;z-index:2;line-height:1;}
.sq .piece.white{color:#ffffff;-webkit-text-stroke:.042em #141213;paint-order:stroke fill;}
.sq .piece.black{color:#141213;-webkit-text-stroke:.042em #ffffff;paint-order:stroke fill;}

.sq .hint{position:absolute;z-index:1;width:26%;height:26%;border-radius:50%;background:var(--hint);}
.sq .hint.capture{width:86%;height:86%;background:none;border:4px solid var(--hint);box-sizing:border-box;}
.sq .coord{position:absolute;z-index:3;font-size:.58rem;font-weight:700;letter-spacing:.03em;}
.sq.light .coord{color:#8d8589;} .sq.dark .coord{color:#7d7579;}
.sq .coord.file{bottom:2px;right:4px;} .sq .coord.rank{top:2px;left:4px;}
.sq.check{box-shadow:inset 0 0 0 4px #cf3b52;}

.status{
  display:flex; align-items:center; gap:.6rem; min-height:2.6rem;
  padding:.7rem .95rem; background:var(--surface); border:1px solid var(--rule);
  border-left:3px solid var(--rose); border-radius:4px; font-size:.94rem;
}
.status .dot{width:.55rem;height:.55rem;border-radius:50%;background:var(--rose);flex:none;}
.status.thinking .dot{animation:pulse 1s ease-in-out infinite;}
.status.over{border-left-color:var(--ink-soft);} .status.over .dot{background:var(--ink-soft);}
@keyframes pulse{0%,100%{opacity:1;transform:scale(1);}50%{opacity:.35;transform:scale(.75);}}
@media (prefers-reduced-motion:reduce){.status.thinking .dot{animation:none;}}

/* ---------- Panneau ---------- */
.panel{flex:1 1 300px; min-width:280px; display:flex; flex-direction:column; gap:1.25rem;}
h1{
  font-family:"Iowan Old Style","Palatino Linotype",Palatino,Georgia,serif;
  font-size:1.85rem; font-weight:600; margin:0; letter-spacing:-.02em;
}
.subtitle{margin:.25rem 0 0; font-size:.86rem; color:var(--ink-soft); line-height:1.55;}

fieldset{border:0;margin:0;padding:0;display:flex;flex-direction:column;gap:.5rem;}
legend, .label{
  font-size:.7rem; text-transform:uppercase; letter-spacing:.1em;
  color:var(--ink); font-weight:700; padding:0;
}
.choices{display:flex;gap:.4rem;flex-wrap:wrap;}
.choice{position:relative;}
.choice input{position:absolute;opacity:0;width:0;height:0;}
.choice span{
  display:block; padding:.42rem .8rem; font-size:.85rem; cursor:pointer;
  background:var(--surface); border:1px solid var(--rule); border-radius:3px;
  transition:all .12s ease;
}
.choice input:checked + span{background:var(--rose);border-color:var(--rose);color:var(--on-rose);}
.choice input:focus-visible + span{outline:2px solid var(--rose);outline-offset:2px;}
.choice span:hover{border-color:var(--rose-soft);}

button.primary{
  padding:.65rem 1rem; font-size:.9rem; font-weight:600; font-family:inherit;
  letter-spacing:.01em;
  color:var(--on-rose); background:var(--rose); border:0; border-radius:3px; cursor:pointer;
  transition:opacity .12s ease;
}
button.primary:hover{opacity:.86;}
button.primary:focus-visible{outline:2px solid var(--rose);outline-offset:2px;}

.moves{
  background:var(--surface); border:1px solid var(--rule); border-radius:4px;
  padding:.7rem .9rem; max-height:190px; overflow-y:auto;
  font-family:ui-monospace,"Cascadia Mono",Consolas,monospace; font-size:.82rem;
  line-height:1.75; color:var(--ink); font-variant-numeric:tabular-nums;
}
.moves:empty::after{content:"Aucun coup joue.";color:var(--ink-soft);font-style:italic;}
.moves .num{color:var(--ink-faint);margin-right:.3rem;}
.moves .mv{margin-right:.85rem;}

.thoughts{display:flex;flex-direction:column;gap:.4rem;}
.thought{display:grid;grid-template-columns:3.6rem 1fr auto;gap:.6rem;align-items:center;font-size:.82rem;}
.thought code{font-family:ui-monospace,Consolas,monospace;background:var(--surface-alt);padding:.1em .35em;border-radius:2px;}
.bar{height:.42rem;background:var(--surface-alt);border-radius:2px;overflow:hidden;}
.bar i{display:block;height:100%;background:var(--rose-soft);}
.thought .pct{color:var(--ink-soft);font-variant-numeric:tabular-nums;font-size:.76rem;}
.thought.played code{background:var(--rose);color:var(--on-rose);}
.thought.played .bar i{background:var(--rose);}
.thought.played .pct{color:var(--rose);font-weight:700;text-transform:uppercase;letter-spacing:.06em;}

.note{font-size:.79rem;color:var(--ink-soft);line-height:1.6;}
/* ---------- Rappel des regles ---------- */
details.rules{
  background:var(--surface); border:1px solid var(--rule); border-radius:4px;
}
details.rules summary{
  cursor:pointer; padding:.72rem .95rem; list-style:none;
  font-size:.7rem; font-weight:700; text-transform:uppercase; letter-spacing:.1em;
  display:flex; align-items:center; justify-content:space-between; gap:.5rem;
}
details.rules summary::-webkit-details-marker{display:none;}
details.rules summary::after{content:"+";font-size:1.1rem;color:var(--rose);line-height:1;}
details.rules[open] summary::after{content:"\2013";}
details.rules summary:focus-visible{outline:2px solid var(--rose);outline-offset:-2px;border-radius:4px;}
.rules-body{
  padding:0 .95rem 1rem; display:flex; flex-direction:column; gap:.6rem;
  border-top:1px solid var(--rule); padding-top:.9rem; margin-top:-.1rem;
}
.rules-body .label{margin:.5rem 0 -.1rem;}
.piece-row{
  display:grid; grid-template-columns:1.7rem 4.6rem 1fr; gap:.55rem;
  align-items:baseline; font-size:.79rem; color:var(--ink-soft); line-height:1.5;
}
.piece-row b{color:var(--ink);font-weight:650;}
.piece-row .glyph{font-size:1.3rem;line-height:1;color:var(--ink);justify-self:center;}

dialog{
  border:1px solid var(--rule); border-radius:5px; padding:1.2rem 1.4rem;
  background:var(--surface); color:var(--ink); max-width:20rem;
}
dialog::backdrop{background:rgba(0,0,0,.45);}
dialog .promo{display:flex;gap:.5rem;margin-top:.9rem;}
dialog .promo button{
  font-size:2rem;line-height:1;padding:.3rem .6rem;cursor:pointer;
  background:var(--surface-alt);border:1px solid var(--rule);border-radius:3px;
}
dialog .promo button:hover{border-color:var(--rose);}
</style>
</head>
<body>
<main class="app">
  <div class="board-side">
    <div class="board" id="board" role="grid" aria-label="Echiquier"></div>
    <p class="status" id="status"><span class="dot"></span><span id="status-text">Chargement...</span></p>
  </div>

  <aside class="panel">
    <div>
      <h1>Chess Bot v1</h1>
      <p class="subtitle">Un Transformer qui choisit son coup sans explorer l'arbre des variantes. En attendant qu'il soit entraine, les bots de reference tiennent le plateau.</p>
    </div>

    <fieldset>
      <legend>Adversaire</legend>
      <div class="choices" id="bots"></div>
    </fieldset>

    <fieldset>
      <legend>Vous jouez</legend>
      <div class="choices">
        <label class="choice"><input type="radio" name="color" value="white" checked><span>Les blancs</span></label>
        <label class="choice"><input type="radio" name="color" value="black"><span>Les noirs</span></label>
      </div>
    </fieldset>

    <button class="primary" id="new-game">Nouvelle partie</button>

    <div>
      <p class="label">Coups joues</p>
      <div class="moves" id="moves"></div>
    </div>

    <div id="thoughts-block" hidden>
      <p class="label">Coups envisages par le bot</p>
      <div class="thoughts" id="thoughts"></div>
      <p class="note">Ce que le bot a considere avant de jouer. Quand le Transformer sera entraine, ces barres afficheront directement les probabilites sorties du reseau.</p>
    </div>

    <details class="rules">
      <summary>Comment jouer aux echecs</summary>
      <div class="rules-body">
        <p class="note"><strong>Le but :</strong> capturer le roi adverse. Quand il est attaque et qu'aucun coup ne peut le sauver, c'est echec et mat, la partie est finie.</p>

        <p class="label">Deplacements</p>
        <div class="piece-row"><span class="glyph">&#9822;</span><b>Cavalier</b><span>En L : deux cases dans un sens, une sur le cote. Seule piece qui saute par-dessus les autres.</span></div>
        <div class="piece-row"><span class="glyph">&#9821;</span><b>Fou</b><span>En diagonale, aussi loin qu'il veut. Reste toute la partie sur sa couleur de case.</span></div>
        <div class="piece-row"><span class="glyph">&#9820;</span><b>Tour</b><span>En ligne droite : horizontalement ou verticalement.</span></div>
        <div class="piece-row"><span class="glyph">&#9819;</span><b>Dame</b><span>Tour + fou reunis. La piece la plus puissante.</span></div>
        <div class="piece-row"><span class="glyph">&#9818;</span><b>Roi</b><span>Une seule case a la fois, dans n'importe quelle direction.</span></div>
        <div class="piece-row"><span class="glyph">&#9823;</span><b>Pion</b><span>Avance d'une case (deux au premier coup), mais capture en diagonale. Ne recule jamais.</span></div>

        <p class="label">Trois coups speciaux</p>
        <p class="note"><strong>Le roque</strong> — le roi se decale de deux cases vers une tour, qui saute de l'autre cote. Met le roi a l'abri. Impossible si le roi a deja bouge ou s'il est en echec.</p>
        <p class="note"><strong>La promotion</strong> — un pion qui atteint la derniere rangee se transforme en la piece de votre choix, presque toujours une dame.</p>
        <p class="note"><strong>La prise en passant</strong> — un pion adverse qui avance de deux cases pour eviter votre pion peut quand meme etre capture, immediatement.</p>

        <p class="label">Valeur des pieces</p>
        <p class="note">Pion 1 &middot; Cavalier 3 &middot; Fou 3 &middot; Tour 5 &middot; Dame 9. Le roi n'a pas de valeur : le perdre, c'est perdre la partie. Ces nombres servent a decider si un echange est rentable, et ce sont exactement ceux que nos bots utilisent pour evaluer une position.</p>

        <p class="label">Dans cette application</p>
        <p class="note">Cliquez sur une de vos pieces : les cases ou elle peut aller s'affichent en rose. Un <strong>petit rond</strong> signale une case libre, un <strong>cercle</strong> une capture. Vous ne pouvez jouer que des coups legaux, donc vous ne pouvez pas vous tromper : essayez, c'est comme ca qu'on apprend.</p>
      </div>
    </details>
  </aside>
</main>

<dialog id="promo-dialog">
  <strong>Promotion du pion</strong>
  <p class="note">En quelle piece voulez-vous le transformer ?</p>
  <div class="promo">
    <button data-piece="q" title="Dame">&#9819;</button>
    <button data-piece="r" title="Tour">&#9820;</button>
    <button data-piece="b" title="Fou">&#9821;</button>
    <button data-piece="n" title="Cavalier">&#9822;</button>
  </div>
</dialog>

<script>
// Un seul jeu de glyphes, toujours les versions PLEINES. La couleur du camp est
// portee par le CSS (remplissage + contour inverse), pas par le caractere.
const GLYPHS = {p:"♟", n:"♞", b:"♝", r:"♜", q:"♛", k:"♚"};
const FILES = "abcdefgh";

const boardEl   = document.getElementById("board");
const statusEl  = document.getElementById("status");
const statusTxt = document.getElementById("status-text");
const movesEl   = document.getElementById("moves");
const thoughtsEl= document.getElementById("thoughts");
const thoughtsBlock = document.getElementById("thoughts-block");
const promoDialog = document.getElementById("promo-dialog");

let state = null;
let selected = null;   // case de depart choisie, ex "e2"
let busy = false;

/* ---------- Appels au serveur ---------- */
async function api(path, payload) {
  const response = await fetch(path, {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify(payload || {}),
  });
  if (!response.ok) throw new Error(await response.text());
  return response.json();
}

/* ---------- Rendu ---------- */
function render() {
  if (!state) return;
  const flipped = state.player_color === "black";
  boardEl.innerHTML = "";

  for (let row = 0; row < 8; row++) {
    for (let col = 0; col < 8; col++) {
      const file = flipped ? 7 - col : col;
      const rank = flipped ? row : 7 - row;
      const name = FILES[file] + (rank + 1);
      const index = rank * 8 + file;

      const sq = document.createElement("div");
      sq.className = "sq " + ((file + rank) % 2 ? "light" : "dark");
      sq.dataset.square = name;
      sq.setAttribute("role", "gridcell");

      if (state.last_move && (state.last_move.slice(0,2) === name || state.last_move.slice(2,4) === name)) {
        sq.classList.add("last");
      }
      if (selected === name) sq.classList.add("selected");
      if (state.check_square === name) sq.classList.add("check");

      const symbol = state.board[index];
      if (symbol) {
        const piece = document.createElement("span");
        piece.className = "piece " + (symbol === symbol.toUpperCase() ? "white" : "black");
        piece.textContent = GLYPHS[symbol.toLowerCase()];
        sq.appendChild(piece);
      }

      // Cases atteignables depuis la case selectionnee
      if (selected) {
        const target = state.legal_moves.find(m => m.slice(0,2) === selected && m.slice(2,4) === name);
        if (target) {
          const hint = document.createElement("span");
          hint.className = "hint" + (symbol ? " capture" : "");
          sq.appendChild(hint);
        }
      }

      // Reperes de coordonnees sur les bords
      if (row === 7) sq.insertAdjacentHTML("beforeend", `<span class="coord file">${FILES[file]}</span>`);
      if (col === 0) sq.insertAdjacentHTML("beforeend", `<span class="coord rank">${rank + 1}</span>`);

      if (state.your_turn && !state.game_over) sq.classList.add("playable");
      sq.addEventListener("click", () => onSquareClick(name));
      boardEl.appendChild(sq);
    }
  }

  // Historique en notation algebrique
  movesEl.innerHTML = state.san.map((san, i) =>
    (i % 2 === 0 ? `<span class="num">${i / 2 + 1}.</span>` : "") + `<span class="mv">${san}</span>`
  ).join("");
  movesEl.scrollTop = movesEl.scrollHeight;

  // Coups envisages par le bot
  if (state.thoughts && state.thoughts.length) {
    thoughtsBlock.hidden = false;
    thoughtsEl.innerHTML = state.thoughts.map(t => `
      <div class="thought${t.played ? " played" : ""}">
        <code>${t.san}</code>
        <span class="bar"><i style="width:${Math.round(t.weight * 100)}%"></i></span>
        <span class="pct">${t.played ? "joue" : Math.round(t.weight * 100) + "%"}</span>
      </div>`).join("");
  } else {
    thoughtsBlock.hidden = true;
  }

  statusTxt.textContent = state.status;
  statusEl.classList.toggle("over", !!state.game_over);
  statusEl.classList.toggle("thinking", busy);
}

/* ---------- Interactions ---------- */
async function onSquareClick(square) {
  if (busy || !state || state.game_over || !state.your_turn) return;

  if (selected) {
    const candidates = state.legal_moves.filter(
      m => m.slice(0, 2) === selected && m.slice(2, 4) === square
    );
    if (candidates.length) {
      let uci = candidates[0];
      if (candidates.length > 1) {          // plusieurs promotions possibles
        const piece = await askPromotion();
        if (!piece) { selected = null; render(); return; }
        uci = selected + square + piece;
      }
      selected = null;
      await playMove(uci);
      return;
    }
  }

  // Selectionner une piece a soi
  selected = state.legal_moves.some(m => m.slice(0, 2) === square) ? square : null;
  render();
}

function askPromotion() {
  return new Promise(resolve => {
    promoDialog.showModal();
    const handler = (event) => {
      const button = event.target.closest("button[data-piece]");
      if (!button) return;
      promoDialog.removeEventListener("click", handler);
      promoDialog.close();
      resolve(button.dataset.piece);
    };
    promoDialog.addEventListener("click", handler);
  });
}

async function playMove(uci) {
  busy = true;
  statusTxt.textContent = "Le bot reflechit...";
  statusEl.classList.add("thinking");
  render();
  try {
    state = await api("/api/move", {uci});
  } catch (error) {
    statusTxt.textContent = "Erreur : " + error.message;
  } finally {
    busy = false;
    render();
  }
}

async function newGame() {
  busy = true;
  selected = null;
  try {
    state = await api("/api/new", {
      bot: document.querySelector('input[name="bot"]:checked').value,
      color: document.querySelector('input[name="color"]:checked').value,
    });
  } finally {
    busy = false;
    render();
  }
}

/* ---------- Demarrage ---------- */
(async function init() {
  const config = await api("/api/bots", {});
  document.getElementById("bots").innerHTML = config.bots.map((bot, i) => `
    <label class="choice">
      <input type="radio" name="bot" value="${bot.id}" ${i === 0 ? "checked" : ""}>
      <span>${bot.label}</span>
    </label>`).join("");
  document.getElementById("new-game").addEventListener("click", newGame);
  await newGame();
})();
</script>
</body>
</html>
"""
