from flask import Flask, render_template, jsonify, session, request

app = Flask(__name__)

# Needed for signed session cookies
import os
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret")


def new_game_state():
    return {
        "board": [""] * 9,
        "current": "X",
        "winner": None,
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

@app.get("/")
def index():
    return render_template("index.html")


@app.get("/api/state")
def api_state():
    return jsonify(get_state())


@app.post("/api/reset")
def api_reset():
    session["game"] = new_game_state()
    return jsonify(session["game"])


@app.post("/api/move")
def api_move():
    state = get_state()

    if state["winner"] is not None:
        return jsonify({"error": "Game is over"}), 409

    data = request.get_json(silent=True) or {}
    idx = data.get("index", None)

    if not isinstance(idx, int) or idx < 0 or idx > 8:
        return jsonify({"error": "Invalid index"}), 400

    if state["board"][idx] != "":
        return jsonify({"error": "Cell is already taken"}), 400

    state["board"][idx] = state["current"]
    state["winner"] = winner_of(state["board"])

    if state["winner"] is None:
        state["current"] = "O" if state["current"] == "X" else "X"

    session["game"] = state
    return jsonify(state)



if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)



