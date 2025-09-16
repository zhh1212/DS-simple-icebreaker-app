import random
from typing import List, Tuple, Dict
import gradio as gr

APP_TITLE = "Icebreaker Game :)"

# -----------------------
# Config: question files (optional; plain text, 1 question per line)
# Leave as None to use fallback seed questions.
# -----------------------
BASIC_FILE = "basic.txt"          # e.g. "basic.txt"
FUN_FILE = "fun.txt"          # e.g. "fun.txt"
DS_FILE = "datascience.txt"             # e.g. "datascience.txt"
BEHAV_FILE = "behav.txt"         # e.g. "behav.txt"

# -----------------------
# Weights
# -----------------------
# Number of categories per round (1..4): lowest chance for 1, highest for 2–3, slightly lower for 4
NUM_Q_OPTIONS = [1, 2, 3, 4]
NUM_Q_WEIGHTS = [1, 5, 5, 3]  # tweak to taste

# Category pick weights (sampled without replacement up to num_q):
# Heavily favor BASIC; others moderate.
CATEGORY_WEIGHTS = {
    "basic": 0.55,
    "fun": 0.2,
    "ds": 0.15,
    "behav": 0.1,
}

CSS = """
/* Big player number */
#current-pick { 
  font-size: clamp(4rem, 14vw, 14rem); 
  text-align: center; 
  font-weight: 800; 
  margin: 0.5rem 0 1rem; 
}

/* Grid of four cards */
.card-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(180px, 1fr));
  gap: 16px;
}

/* Card container + flip */
.card { perspective: 1000px; }

/* Tile (the clickable details element) */
.card details {
  position: relative;
  width: 100%;
  height: 220px;                 /* set your card height here */
  border-radius: 16px;
  box-shadow: 0 6px 18px rgba(0,0,0,0.12);
  overflow: hidden;              /* keep rounded corners on flip */
}

/* Summary must fill the whole tile so faces do too */
.card summary {
  list-style: none;
  cursor: pointer;
  display: block;
  height: 100%;
  padding: 0;
  margin: 0;
}
.card summary::-webkit-details-marker { display: none; }

.inner {
  position: relative;
  width: 100%;
  height: 100%;
  transform-style: preserve-3d;
  transition: transform 0.6s;
}
details[open] .inner { transform: rotateY(180deg); }

/* Faces cover the entire card */
.face {
  position: absolute; inset: 0;
  -webkit-backface-visibility: hidden; backface-visibility: hidden;
  display: flex; 
  align-items: center; 
  justify-content: center;
  padding: 20px; 
  text-align: center; 
  color: #fff; 
  font-weight: 700; 
  font-size: 1.1rem;
  border-radius: 16px; 
  box-sizing: border-box;
}

/* Front = whole-card color */
.front { background: #c62828; }              /* red = not picked */
.front.picked-basic  { background: #2e7d32; } /* green */
.front.picked-fun    { background: #2e7d32; } 
.front.picked-ds     { background: #2e7d32; } 
.front.picked-behav  { background: #2e7d32; } 

/* Back = whole-card content */
.back  { 
  background: #111; 
  transform: rotateY(180deg);
  line-height: 1.4; 
  padding: 20px;
  font-weight: 600;
  font-size: 1rem;
  display: flex;                    /* center the question nicely */
  align-items: center; 
  justify-content: center;
  white-space: normal;
  overflow: auto;                   /* scroll if too long */
}
"""

def parse_players(text: str) -> List[int]:
    text = (text or "").strip()
    if not text:
        raise ValueError("Enter a count (e.g., 6), a range (e.g., 1-6), or a list (e.g., 1,3,7).")
    parts = [p.strip() for p in text.split(",") if p.strip()]
    numbers = set()
    if len(parts) == 1 and parts[0].isdigit():
        count = int(parts[0])
        if count <= 0:
            raise ValueError("Count must be a positive integer.")
        return list(range(1, count + 1))
    for part in parts:
        if "-" in part:
            a, b = part.split("-", 1)
            if not a.strip().isdigit() or not b.strip().isdigit():
                raise ValueError(f"Invalid range: {part}")
            start, end = int(a), int(b)
            if start > end:
                start, end = end, start
            numbers.update(range(start, end + 1))
        else:
            if not part.isdigit():
                raise ValueError(f"Invalid number: {part}")
            numbers.add(int(part))
    if not numbers:
        raise ValueError("No valid players found.")
    return sorted(numbers)

def _load_file_lines(path: str) -> List[str]:
    with open(path, "r", encoding="utf-8") as f:
        lines = [ln.strip() for ln in f.readlines()]
    return [ln for ln in lines if ln]

def load_question_pools() -> Dict[str, List[str]]:
    pools = {}
    try:
        pools["basic"] = _load_file_lines(BASIC_FILE) if BASIC_FILE else [
            "What’s your favorite way to spend a weekend?",
            "Coffee or tea? Why?",
            "What’s a small win you’re proud of this week?",
        ]
    except Exception:
        pools["basic"] = []
    try:
        pools["fun"] = _load_file_lines(FUN_FILE) if FUN_FILE else [
            "If you had a superpower for a day, what would it be?",
            "What’s the funniest thing you believed as a kid?",
            "Choose a theme song for your life right now.",
        ]
    except Exception:
        pools["fun"] = []
    try:
        pools["ds"] = _load_file_lines(DS_FILE) if DS_FILE else [
            "What’s one dataset you’d love to analyze and why?",
            "Bias vs variance—give a real-world example.",
            "Favorite visualization for time-series and why?",
        ]
    except Exception:
        pools["ds"] = []
    try:
        pools["behav"] = _load_file_lines(BEHAV_FILE) if BEHAV_FILE else [
            "Tell me about a time you resolved a conflict at work.",
            "Describe a failure and what you learned.",
            "How do you handle competing priorities?",
        ]
    except Exception:
        pools["behav"] = []
    return pools

def set_players(players_text: str):
    try:
        players = parse_players(players_text)
    except ValueError as e:
        pools = load_question_pools()
        used = {"basic":[], "fun":[], "ds":[], "behav":[]}
        return "—", f"❌ {e}", players_text, [], pools, used, _cards_html()
    status = f"✅ Loaded {len(players)} players."
    pools = load_question_pools()
    used = {"basic":[], "fun":[], "ds":[], "behav":[]}
    cards = _cards_html()
    return "—", status, players_text, players, pools, used, cards

def weighted_num_questions() -> int:
    return random.choices(NUM_Q_OPTIONS, weights=NUM_Q_WEIGHTS, k=1)[0]

def weighted_category_sample(k: int) -> List[str]:
    # sample without replacement according to CATEGORY_WEIGHTS
    cats = list(CATEGORY_WEIGHTS.keys())
    weights = CATEGORY_WEIGHTS.copy()
    chosen = []
    for _ in range(min(k, len(cats))):
        total = sum(weights[c] for c in cats)
        r = random.random() * total
        cum = 0.0
        pick = cats[0]
        for c in cats:
            cum += weights[c]
            if r <= cum:
                pick = c
                break
        chosen.append(pick)
        # remove picked category from next draw
        cats.remove(pick)
    return chosen

def _take_random(qpool: List[str], used: List[str]) -> str:
    # Return and remove a random question from pool; record in used
    if not qpool:
        return "No more questions in this category."
    q = random.choice(qpool)
    qpool.remove(q)
    used.insert(0, q)
    return q

def allocate_questions(players_set: List[int], picked_order: List[int], pools: Dict[str, List[str]], used: Dict[str, List[str]], avoid_repeats: bool):
    # original player picking result
    if not players_set:
        return "—", "⚠️ Please set players first.", picked_order, _cards_html(picked=set())
    # pick player with same logic
    if avoid_repeats:
        remaining = [p for p in players_set if p not in picked_order]
        if not remaining:
            last = picked_order[0] if picked_order else "—"
            return str(last), "ℹ️ Everyone has been picked! Reset or disable 'Avoid repeats' to continue.", picked_order, _cards_html(picked=set())
        player = random.choice(remaining)
    else:
        player = random.choice(players_set)
    new_picked = [player] + picked_order

    # decide how many categories & which ones
    k = weighted_num_questions()
    cats = weighted_category_sample(k)

    # ensure BASIC heavily likely: already baked in weights; also if basic pool empty, it's okay.
    chosen_questions = {}
    for c in cats:
        q = _take_random(pools[c], used[c])
        chosen_questions[c] = q

    status = f"🎯 Player {player} — Assigned {len(cats)} question{'s' if len(cats)>1 else ''}: " + ", ".join(cat_label(c) for c in cats)

    # Build updated cards: selected ones flip-ready with question & color; others red "Not picked"
    cards = _cards_html(chosen_questions, picked=set(cats))
    return str(player), status, new_picked, cards

def reset_all():
    pools = load_question_pools()
    used = {"basic":[], "fun":[], "ds":[], "behav":[]}
    # current, status, players_text, players, pools, used, cards, picked_players
    return "—", "🔄 Reset complete.", "", [], pools, used, _cards_html(), []


def cat_label(key: str) -> str:
    return {
        "basic": "Basic",
        "fun": "Fun",
        "ds": "Data Science",
        "behav": "Behavioral",
    }[key]

def _card_html_one(card_id: str, title: str, question: str = "Click to flip", picked_class: str = "") -> str:
    return f"""
<div class="card">
  <details id="{card_id}">
    <summary>
      <div class="inner">
        <div class="face front {picked_class}">
          <span>{title}</span>
        </div>
        <div class="face back">{question}</div>
      </div>
    </summary>
  </details>
</div>
"""

def _cards_html(chosen: Dict[str, str] = None, picked: set = None) -> str:
    chosen = chosen or {}
    picked = picked or set()

    def card(key, title):
        picked_class = f"picked-{('behav' if key=='behav' else key)}" if key in picked else ""
        q = chosen.get(key, "Not picked this round") if key in picked else "Not picked this round"
        return _card_html_one(f"flip-{key}", title, q, picked_class)

    return f"""
<div class="card-grid">
  {card("basic", "Basic")}
  {card("fun", "Fun")}
  {card("ds", "Data Science")}
  {card("behav", "Behavioral")}
</div>
"""

# ---------------- UI ----------------

with gr.Blocks(theme=gr.themes.Soft(), css=CSS, title=APP_TITLE) as demo:
    gr.Markdown(f"# {APP_TITLE}")

    gr.Markdown("""
    ## 📜 Game Rules
    1. Enter the number of players (e.g., `1-6` for 6 players).  
    2. Randomly select a player.
    3. There will be 4 types of questions, the selected player needs to flip the card in green and answer the question!
    4. If a player got picked twice in a row, the player can choose another player to answer the questions for this round.
    """)

    with gr.Row():
        players_text = gr.Textbox(
            label="Players (range/list/count)",
            value="1-6",
            placeholder='Examples: "1-6" • "8" (means 1..8) • "1,3,7" • "1-3, 6, 10-12"',
        )
        avoid_repeats = gr.Checkbox(label="Avoid repeats (players)", value=True)

    with gr.Row():
        set_btn = gr.Button("Set Players", variant="primary")
        pick_btn = gr.Button("Pick & Allocate Questions")
        reset_btn = gr.Button("Reset")

    current = gr.HTML("<div id='current-pick'>—</div>")
    status = gr.Markdown("")

    # Cards container
    cards_html = gr.HTML(_cards_html())

    # State:
    state_players = gr.State([])                         # players list
    state_picked_players = gr.State([])                  # already picked players (for avoid repeats)
    state_pools = gr.State(load_question_pools())        # remaining questions per category
    state_used = gr.State({"basic":[], "fun":[], "ds":[], "behav":[]})  # used questions per category

    # Wiring
    def _set_players_ui(text):
        cur, stat, text_keep, players, pools, used, cards = set_players(text)
        return (
            f"<div id='current-pick'>{cur}</div>",
            stat,
            text_keep,
            players,
            pools,
            used,
            cards,
            [],   # <- clear picked players on (re)configure
        )

    def _pick_ui(ar, players, picked_order, pools, used):
        cur, stat, picked_new, cards = allocate_questions(players, picked_order, pools, used, ar)
        return (
            f"<div id='current-pick'>{cur}</div>",
            stat,
            picked_new,
            cards,
        )

    def _reset_ui():
        cur, stat, text_keep, players, pools, used, cards, picked_players = reset_all()
        return (
            f"<div id='current-pick'>{cur}</div>",
            stat,
            text_keep,
            players,
            pools,
            used,
            cards,
            picked_players,
        )

    set_btn.click(
        _set_players_ui,
        inputs=[players_text],
        outputs=[current, status, players_text, state_players, state_pools, state_used, cards_html, state_picked_players],
    )

    pick_btn.click(
        _pick_ui,
        inputs=[avoid_repeats, state_players, state_picked_players, state_pools, state_used],
        outputs=[current, status, state_picked_players, cards_html],
    )

    reset_btn.click(
        _reset_ui,
        inputs=[],
        outputs=[current, status, players_text, state_players, state_pools, state_used, cards_html, state_picked_players],
    )

if __name__ == "__main__":
    demo.launch()
