from flask import Flask, jsonify, request, render_template
import time
import threading

app = Flask(__name__)

# Game state
game_state = {
    "players": {"X": None, "O": None},
    "board": [""] * 9,
    "current_turn": "X",
    "winner": None,
    "last_activity": {"X": time.time(), "O": time.time()}
}

# Handle player joining
@app.route("/join", methods=["POST"])
def join():
    data = request.get_json()
    name = data.get("name")
    
    if name in game_state["players"].values():
        return jsonify({"success": False, "message": "Name already taken"}), 400
    
    if game_state["players"]["X"] is None:
        game_state["players"]["X"] = name
        game_state["last_activity"]["X"] = time.time()
        return jsonify({"success": True, "symbol": "X"})
    elif game_state["players"]["O"] is None:
        game_state["players"]["O"] = name
        game_state["last_activity"]["O"] = time.time()
        return jsonify({"success": True, "symbol": "O"})
    
    return jsonify({"success": False, "message": "Game is full"}), 400

# Handle player leaving
@app.route("/leave", methods=["POST"])
def leave():
    try:
        data = request.get_json()
        if not data:
            app.logger.error("Leave request missing data")
            return jsonify({"success": False, "message": "Missing data"}), 400

        symbol = data.get("symbol")
        if not symbol:
            app.logger.error("Leave request missing 'symbol' field.")
            return jsonify({"success": False, "message": "Missing symbol"}), 400
        
        if symbol not in game_state["players"]:
            app.logger.error(f"Leave failed: Invalid symbol '{symbol}'.")
            return jsonify({"success": False, "message": "Invalid player symbol"}), 400

        player_name = game_state["players"][symbol]
        if player_name is None:
            app.logger.error(f"Leave failed: Player {symbol} already left.")
            return jsonify({"success": False, "message": "Player already left"}), 400

        app.logger.info(f"Player {symbol} ({player_name}) left the game.")
        game_state["players"][symbol] = None
        game_state["last_activity"][symbol] = time.time()

        reset_game()
        return jsonify({"success": True})
    
    except Exception as e:
        app.logger.error(f"Error in leave endpoint: {str(e)}")
        return jsonify({"success": False, "message": "Server error"}), 500

# Heartbeat endpoint
@app.route("/heartbeat", methods=["POST"])
def heartbeat():
    data = request.get_json()
    symbol = data.get("symbol")
    if symbol in game_state["players"]:
        game_state["last_activity"][symbol] = time.time()
        return jsonify({"success": True})
    return jsonify({"success": False, "message": "Invalid symbol"}), 400

# Handle moves
@app.route("/make_move", methods=["POST"])
def make_move():
    data = request.get_json()
    symbol = data["symbol"]
    index = data["index"]
    
    if game_state["board"][index] != "":
        return jsonify({"success": False, "message": "Invalid move"}), 400

    game_state["board"][index] = symbol
    game_state["last_activity"][symbol] = time.time()

    winner = check_winner()
    if winner:
        game_state["winner"] = winner
    else:
        game_state["current_turn"] = "X" if symbol == "O" else "O"
    
    return jsonify({"success": True})

# Get game state
@app.route("/get_state", methods=["GET"])
def get_state():
    return jsonify(game_state)

# Reset game
@app.route("/reset", methods=["POST"])
def reset_game():
    game_state["board"] = [""] * 9
    game_state["winner"] = None
    game_state["current_turn"] = "X"
    game_state["last_activity"] = {"X": time.time(), "O": time.time()}
    return jsonify({"success": True})

# Check for winner
def check_winner():
    win_conditions = [(0, 1, 2), (3, 4, 5), (6, 7, 8), (0, 3, 6), (1, 4, 7), (2, 5, 8), (0, 4, 8), (2, 4, 6)]
    for condition in win_conditions:
        a, b, c = condition
        if game_state["board"][a] == game_state["board"][b] == game_state["board"][c] != "":
            return game_state["board"][a]
    return None

# Inactivity check
def check_inactive_players():
    current_time = time.time()
    for symbol in ["X", "O"]:
        player_name = game_state["players"][symbol]
        last_active = game_state["last_activity"][symbol]
        if player_name and current_time - last_active > 30:  # 30 seconds inactivity
            app.logger.info(f"Player {symbol} ({player_name}) disconnected due to inactivity.")
            game_state["players"][symbol] = None
            reset_game()

# Background thread for inactivity checks
def periodic_check():
    while True:
        time.sleep(10)
        check_inactive_players()

threading.Thread(target=periodic_check, daemon=True).start()

# Main page
@app.route("/")
def index():
    return render_template("index.html")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
