import os
import json
import uuid
from redis import Redis

from flask import Flask, render_template, jsonify, session, request

app = Flask(__name__)

app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret")

redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
r = Redis.from_url(redis_url, decode_responses=True)

GAME_KEY_PREFIX = "game:"


# Needed for signed session cookies
import os
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret")


def new_game_state():
    return {
        "board": [""] * 9,
        "current": "X",
        "winner": None,
        "players": {"X": None, "O": None},  # tokens for players
    }


def get_state():
    if "game" not in session:
        session["game"] = new_game_state()
    return session["game"]

def winner_of(board):
    lines = [
        (0, 1, 2), (3, 4, 5), (6, 7, 8),
        (0, 3, 6), (1, 4, 7), (2, 5, 8),
        (0, 4, 8), (2, 4, 6),
    ]
    for a, b, c in lines:
        if board[a] and board[a] == board[b] == board[c]:
            return board[a]
    if all(v != "" for v in board):
        return "DRAW"
    return None

def game_key(game_id: str) -> str:
    return f"{GAME_KEY_PREFIX}{game_id}"


def load_game(game_id: str):
    raw = r.get(game_key(game_id))
    if not raw:
        return None
    return json.loads(raw)


def save_game(game_id: str, state: dict):
    r.set(game_key(game_id), json.dumps(state))

def assign_player(state: dict) -> tuple[str, str]:
    """
    Returns (role, token). role is one of: X, O, SPECTATOR.
    """
    if state["players"]["X"] is None:
        token = uuid.uuid4().hex
        state["players"]["X"] = token
        return "X", token
    if state["players"]["O"] is None:
        token = uuid.uuid4().hex
        state["players"]["O"] = token
        return "O", token
    return "SPECTATOR", ""


def role_for_token(state: dict, token: str) -> str:
    if token and token == state["players"].get("X"):
        return "X"
    if token and token == state["players"].get("O"):
        return "O"
    return "SPECTATOR"



@app.get("/")
def index():
    return render_template("index.html")


@app.get("/api/state")
def api_state():
    return jsonify(get_state())

@app.post("/api/games")
def api_create_game():
    game_id = uuid.uuid4().hex
    state = new_game_state()
    save_game(game_id, state)
    return jsonify({"game_id": game_id, "state": state})

@app.get("/api/games/<game_id>")
def api_get_game(game_id):
    state = load_game(game_id)
    if state is None:
        return jsonify({"error": "Game not found"}), 404
    return jsonify(state)


@app.post("/api/games/<game_id>/reset")
def api_reset_game(game_id):
    state = load_game(game_id)
    if state is None:
        return jsonify({"error": "Game not found"}), 404
    state = new_game_state()
    save_game(game_id, state)
    return jsonify(state)


@app.post("/api/games/<game_id>/move")
def api_move_game(game_id):
    state = load_game(game_id)
    data = request.get_json(silent=True) or {}
    token = data.get("token", "")
    role = role_for_token(state, token)

    if role not in ("X", "O"):
        return jsonify({"error": "You are not a player"}), 403

    if state["current"] != role:
        return jsonify({"error": "Not your turn"}), 403
    
    if state is None:
        return jsonify({"error": "Game not found"}), 404

    if state["winner"] is not None:
        return jsonify({"error": "Game is over"}), 409

    idx = data.get("index", None)

    if not isinstance(idx, int) or idx < 0 or idx > 8:
        return jsonify({"error": "Invalid index"}), 400

    if state["board"][idx] != "":
        return jsonify({"error": "Cell is already taken"}), 400

    state["board"][idx] = state["current"]
    state["winner"] = winner_of(state["board"])

    if state["winner"] is None:
        state["current"] = "O" if state["current"] == "X" else "X"

    save_game(game_id, state)
    return jsonify(state)

@app.post("/api/games/<game_id>/join")
def api_join_game(game_id):
    state = load_game(game_id)
    if state is None:
        return jsonify({"error": "Game not found"}), 404

    role, token = assign_player(state)
    save_game(game_id, state)
    return jsonify({"role": role, "token": token})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)



