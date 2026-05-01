#!/usr/bin/env python3
"""Reversi/Othello game handler for GitHub profile README.

No external dependencies — pure stdlib only.

Issue title formats:
  reversi|move|{square}|1   e.g. reversi|move|d3|1
  reversi|new_game|1
"""

import os
import re

GITHUB_ACTOR = os.environ.get("GITHUB_ACTOR", "anonymous")
ISSUE_TITLE = os.environ.get("ISSUE_TITLE", "")

BOARD_FILE   = "reversi_games/board.txt"
TURN_FILE    = "reversi_games/turn.txt"
RECENT_FILE  = "reversi_games/recent_moves.txt"
LEADER_FILE  = "reversi_games/leaderboard.txt"
README       = "README.md"

REPO_URL = "https://github.com/sametsarikaya/sametsarikaya"

EMPTY = "🟩"
BLACK = "⚫"
WHITE = "⚪"
VALID = "🔵"

DIRS = [(-1,-1),(-1,0),(-1,1),(0,-1),(0,1),(1,-1),(1,0),(1,1)]


# ── Board helpers ─────────────────────────────────────────────────────────────

def new_board() -> list:
    b = ['.'] * 64
    b[27] = 'B'  # d5
    b[28] = 'W'  # e5
    b[35] = 'W'  # d4
    b[36] = 'B'  # e4
    return b

def idx(row: int, col: int) -> int:
    return row * 8 + col

def get_flips(board: list, row: int, col: int, color: str) -> list:
    if board[idx(row, col)] != '.':
        return []
    opp = 'W' if color == 'B' else 'B'
    flips = []
    for dr, dc in DIRS:
        r, c = row + dr, col + dc
        line = []
        while 0 <= r < 8 and 0 <= c < 8 and board[idx(r, c)] == opp:
            line.append(idx(r, c))
            r += dr
            c += dc
        if line and 0 <= r < 8 and 0 <= c < 8 and board[idx(r, c)] == color:
            flips.extend(line)
    return flips

def valid_moves(board: list, color: str) -> list:
    return [(r, c) for r in range(8) for c in range(8) if get_flips(board, r, c, color)]

def apply_move(board: list, row: int, col: int, color: str) -> bool:
    flips = get_flips(board, row, col, color)
    if not flips:
        return False
    board[idx(row, col)] = color
    for i in flips:
        board[i] = color
    return True

def score(board: list) -> tuple:
    return board.count('B'), board.count('W')

def square_to_str(row: int, col: int) -> str:
    return chr(ord('a') + col) + str(8 - row)

def parse_square(s: str):
    s = s.lower().strip()
    if len(s) != 2 or not s[1].isdigit():
        return None
    col  = ord(s[0]) - ord('a')
    row  = 8 - int(s[1])
    if not (0 <= col <= 7 and 0 <= row <= 7):
        return None
    return row, col


# ── Persistence ───────────────────────────────────────────────────────────────

def load_board() -> list:
    try:
        with open(BOARD_FILE) as f:
            data = f.read().strip()
        if len(data) == 64 and all(c in '.BW' for c in data):
            return list(data)
    except FileNotFoundError:
        pass
    return new_board()

def load_turn() -> str:
    try:
        with open(TURN_FILE) as f:
            t = f.read().strip()
        if t in ('B', 'W'):
            return t
    except FileNotFoundError:
        pass
    return 'B'

def save_state(board: list, turn: str):
    os.makedirs("reversi_games", exist_ok=True)
    with open(BOARD_FILE, 'w') as f:
        f.write(''.join(board))
    with open(TURN_FILE, 'w') as f:
        f.write(turn)

def append_recent_move(square: str, color: str, username: str):
    os.makedirs("reversi_games", exist_ok=True)
    emoji = BLACK if color == 'B' else WHITE
    try:
        with open(RECENT_FILE) as f:
            lines = [l for l in f.read().splitlines() if '|' in l]
    except FileNotFoundError:
        lines = []
    new = f"| {emoji} {square.upper()} | [@{username}](https://github.com/{username}) |"
    with open(RECENT_FILE, 'w') as f:
        f.write("\n".join([new] + lines[:4]) + "\n")

def increment_leaderboard(username: str):
    data: dict = {}
    try:
        with open(LEADER_FILE) as f:
            for line in f:
                if '|' in line:
                    cnt, user = line.strip().split('|', 1)
                    try:
                        data[user.strip()] = int(cnt.strip())
                    except ValueError:
                        pass
    except FileNotFoundError:
        pass
    data[username] = data.get(username, 0) + 1
    os.makedirs("reversi_games", exist_ok=True)
    with open(LEADER_FILE, 'w') as f:
        for user, cnt in sorted(data.items(), key=lambda x: x[1], reverse=True):
            f.write(f"{cnt}|{user}\n")


# ── Rendering ─────────────────────────────────────────────────────────────────

def render_board(board: list, valid: list) -> str:
    valid_set = {idx(r, c) for r, c in valid}
    rows = [
        "|   | **A** | **B** | **C** | **D** | **E** | **F** | **G** | **H** |",
        "| :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: |",
    ]
    for row in range(7, -1, -1):
        cells = [f"| **{8 - row}**"]
        for col in range(8):
            i = idx(row, col)
            if board[i] == 'B':
                cells.append(BLACK)
            elif board[i] == 'W':
                cells.append(WHITE)
            elif i in valid_set:
                cells.append(VALID)
            else:
                cells.append(EMPTY)
        cells.append("")
        rows.append(" | ".join(cells))
    return "\n".join(rows)

def render_moves_table(valid: list, turn: str) -> str:
    color_name = "Black \u26ab" if turn == 'B' else "White \u26aa"
    if not valid:
        return f"**No valid moves for {color_name} \u2014 turn skipped automatically.**"

    # Group by column letter for compact display (like the chess example)
    lines = [
        f"#### **{color_name}** to move \u2014 click a square below:",
        "",
        "| Square | Play |",
        "| :----: | :--- |",
    ]
    for row, col in sorted(valid, key=lambda rc: (rc[1], rc[0])):
        sq = square_to_str(row, col).upper()
        uci = square_to_str(row, col)
        url = (
            f"{REPO_URL}/issues/new"
            f"?title=reversi%7Cmove%7C{uci}%7C1"
            f"&body=Just+push+%27Submit+new+issue%27.+You+don%27t+need+to+do+anything+else."
        )
        lines.append(f"| **{sq}** | [\u25b6 Play {sq}]({url}) |")
    return "\n".join(lines)


# ── README section builder ────────────────────────────────────────────────────

def build_section(board: list, turn: str) -> str:
    vm = valid_moves(board, turn)
    active_turn = turn

    if not vm:
        other = 'W' if turn == 'B' else 'B'
        vm = valid_moves(board, other)
        if vm:
            active_turn = other
        # else game over — vm stays empty

    b_cnt, w_cnt = score(board)

    BAR_WIDTH = 20
    total = b_cnt + w_cnt
    b_bar = round(b_cnt / total * BAR_WIDTH) if total else BAR_WIDTH // 2
    w_bar = BAR_WIDTH - b_bar
    score_bar = f"`⚫{'█' * b_bar}{'░' * w_bar}⚪`"

    if not vm:
        if b_cnt > w_cnt:
            status_line = f"🏆 **Black Wins!** ⚫ {b_cnt} — {w_cnt} ⚪ — New game starting…"
        elif w_cnt > b_cnt:
            status_line = f"🏆 **White Wins!** ⚪ {w_cnt} — {b_cnt} ⚫ — New game starting…"
        else:
            status_line = f"🤝 **Draw!** ⚫ {b_cnt} — {w_cnt} ⚪ — New game starting…"
        board_md = render_board(board, [])
        moves_note = "🔄 _Auto-restarting…_"
    else:
        color_name = "Black ⚫" if active_turn == 'B' else "White ⚪"
        status_line = f"**Turn: {color_name}** &nbsp;|&nbsp; **Score: ⚫ {b_cnt} — {w_cnt} ⚪**"
        board_md = render_board(board, vm)
        moves_note = render_moves_table(vm, active_turn)

    # Recent moves
    try:
        with open(RECENT_FILE) as f:
            recent_raw = f.read().strip()
    except FileNotFoundError:
        recent_raw = ""

    if recent_raw:
        recent_md = "| Move | Who |\n| :---- | :-- |\n" + recent_raw
    else:
        recent_md = "_No moves yet — be the first!_"

    # Leaderboard
    try:
        with open(LEADER_FILE) as f:
            lb_lines = [l.strip() for l in f if '|' in l]
    except FileNotFoundError:
        lb_lines = []

    if lb_lines:
        lb_rows = []
        for line in lb_lines[:10]:
            cnt, user = line.split('|', 1)
            lb_rows.append(f"| {cnt.strip()} | [@{user.strip()}](https://github.com/{user.strip()}) |")
        lb_md = "| Moves | Who |\n| :---: | :-- |\n" + "\n".join(lb_rows)
    else:
        lb_md = "_Nobody yet._"

    return f"""\
<!-- REVERSI_START -->

<div align="center">

## 🎮 Community Reversi Tournament

> Anyone can play — click a 🔵 square to make your move! 👇

{status_line}

{score_bar}

<br>

{board_md}

{moves_note}

<br>

<details>
<summary><b>📖 How to play Reversi — click to expand</b></summary>
<br>

**Making a move:**

**1.** Click a 🔵 highlighted square on the board above<br>
**2.** A GitHub Issue opens — press **"Submit new issue"**<br>
**3.** The board auto-updates! ♻️

---

**Legend:**

| | |
|:-:|:--|
| ⚫ | Black disc — plays first |
| ⚪ | White disc |
| 🔵 | Valid move — click to play here |
| 🟩 | Empty square |

**Goal:** Have the most discs on the board when the game ends!

**How capturing works:**

Place your disc on a 🔵 square. Any opponent discs **sandwiched in a straight line** between your new disc and one of your existing discs — in any of the 8 directions (↑ ↓ ← → ↗ ↙ ↘ ↖) — are **flipped** to your color.

<pre>
Example — Black plays C4:

  Before        After
🟩 ⚫ 🟩      🟩 ⚫ 🟩
⚪ ⚪ 🔵  →  ⚫ ⚫ ⚫
🟩 🟩 🟩      🟩 🟩 🟩

The two ⚪ discs are sandwiched → flipped to ⚫!
</pre>

- You **must** flip at least one disc — only 🔵 squares are playable
- If you have **no valid moves**, your turn is skipped automatically
- When **neither player** can move, the game ends and **auto-restarts** 🔄
- The player with the **most discs wins** 🏆

</details>

</div>

<br>

<table>
<tr>
<td valign="top" width="50%">

**🕐 Recent Moves**

{recent_md}

</td>
<td valign="top" width="50%">

**🏆 Leaderboard**

{lb_md}

</td>
</tr>
</table>

<!-- REVERSI_END -->"""


def update_readme(board: list, turn: str):
    try:
        with open(README) as f:
            content = f.read()
    except FileNotFoundError:
        content = ""

    section = build_section(board, turn)
    start_tag = "<!-- REVERSI_START -->"
    end_tag   = "<!-- REVERSI_END -->"

    if start_tag in content and end_tag in content:
        s = content.index(start_tag)
        e = content.index(end_tag) + len(end_tag)
        content = content[:s] + section + content[e:]
    else:
        content = content.rstrip() + "\n\n" + section + "\n"

    with open(README, 'w') as f:
        f.write(content)
    print("README.md updated.")


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> bool:
    print(f"Issue title : {ISSUE_TITLE!r}")
    print(f"Actor       : {GITHUB_ACTOR}")

    # New game
    if re.match(r"reversi\|new_game\|\d+", ISSUE_TITLE, re.IGNORECASE):
        board = new_board()
        save_state(board, 'B')
        update_readme(board, 'B')
        print("New game started.")
        return True

    # Move
    m = re.match(r"reversi\|move\|([a-h][1-8])\|\d+", ISSUE_TITLE, re.IGNORECASE)
    if not m:
        print(f"Unrecognised issue title: {ISSUE_TITLE!r}")
        return False

    sq_str = m.group(1).lower()
    board  = load_board()
    turn   = load_turn()

    parsed = parse_square(sq_str)
    if parsed is None:
        print(f"Cannot parse square: {sq_str}")
        return False
    row, col = parsed

    # Skip turn if current player has no moves
    vm = valid_moves(board, turn)
    if not vm:
        other = 'W' if turn == 'B' else 'B'
        if valid_moves(board, other):
            print(f"{turn} has no moves — skipping to {other}.")
            turn = other
        else:
            b_cnt, w_cnt = score(board)
            if b_cnt > w_cnt:
                print(f"Game over — Black wins {b_cnt}–{w_cnt}. Auto-restarting.")
            elif w_cnt > b_cnt:
                print(f"Game over — White wins {w_cnt}–{b_cnt}. Auto-restarting.")
            else:
                print(f"Game over — Draw {b_cnt}–{w_cnt}. Auto-restarting.")
            board = new_board()
            turn = 'B'
            save_state(board, turn)
            update_readme(board, turn)
            return True

    vm = valid_moves(board, turn)
    if (row, col) not in vm:
        print(f"Illegal move {sq_str.upper()} for {turn}. Legal: {[square_to_str(r,c) for r,c in vm]}")
        return False

    apply_move(board, row, col, turn)
    b_cnt, w_cnt = score(board)

    # Determine next turn
    next_turn = 'W' if turn == 'B' else 'B'
    if not valid_moves(board, next_turn):
        if valid_moves(board, turn):
            print(f"{next_turn} has no moves — {turn} plays again.")
            next_turn = turn
        else:
            # Neither player can move — auto-restart
            b_cnt2, w_cnt2 = score(board)
            if b_cnt2 > w_cnt2:
                print(f"Game over — Black wins {b_cnt2}–{w_cnt2}. Auto-restarting.")
            elif w_cnt2 > b_cnt2:
                print(f"Game over — White wins {w_cnt2}–{b_cnt2}. Auto-restarting.")
            else:
                print(f"Game over — Draw {b_cnt2}–{w_cnt2}. Auto-restarting.")
            append_recent_move(sq_str, turn, GITHUB_ACTOR)
            increment_leaderboard(GITHUB_ACTOR)
            board = new_board()
            next_turn = 'B'
            save_state(board, next_turn)
            update_readme(board, next_turn)
            return True

    save_state(board, next_turn)
    append_recent_move(sq_str, turn, GITHUB_ACTOR)
    increment_leaderboard(GITHUB_ACTOR)
    update_readme(board, next_turn)

    print(f"Move: {sq_str.upper()} by {'⚫' if turn=='B' else '⚪'} @{GITHUB_ACTOR} | Score: ⚫{b_cnt} ⚪{w_cnt}")
    return True


if __name__ == "__main__":
    raise SystemExit(0 if main() else 1)
