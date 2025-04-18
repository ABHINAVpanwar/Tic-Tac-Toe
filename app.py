from flask import Flask, jsonify, request, render_template
import time
import threading

app = Flask(__name__)

# Example data to track game state
game_state = {
    "players": {"X": None, "O": None},  # Player names
    "board": [""] * 9,  # 3x3 board (empty at the start)
    "current_turn": "X",  # X always starts
    "winner": None,
    "last_activity": {"X": time.time(), "O": time.time()}  # Track last activity time for each player
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
        return jsonify({"success": True, "symbol": "X"})
    elif game_state["players"]["O"] is None:
        game_state["players"]["O"] = name
        return jsonify({"success": True, "symbol": "O"})
    
    return jsonify({"success": False, "message": "Game is full"}), 400

@app.route("/leave", methods=["POST"])
def leave():
    data = request.get_json()

    if not data or "symbol" not in data:
        print("Leave request missing 'symbol' field.")
        return jsonify({"success": False, "message": "Missing symbol"}), 400

    symbol = data["symbol"]
    
    if symbol not in game_state["players"]:
        print(f"Leave failed: Invalid symbol '{symbol}'.")
        return jsonify({"success": False, "message": "Invalid player symbol"}), 400

    if game_state["players"][symbol] is None:
        print(f"Leave failed: Player {symbol} already left.")
        return jsonify({"success": False, "message": "Player already left"}), 400

    print(f"Player {symbol} ({game_state['players'][symbol]}) left the game.")
    game_state["players"][symbol] = None
    game_state["last_activity"][symbol] = time.time()

    reset_game()
    return jsonify({"success": True})


# Update the state periodically to detect players who are inactive
def check_inactive_players():
    current_time = time.time()
    
    for symbol in ["X", "O"]:
        if game_state["players"][symbol] and current_time - game_state["last_activity"][symbol] > 60:  # 1 minute of inactivity
            # Player is considered inactive, reset game
            game_state["players"][symbol] = None
            print(f"Player {symbol} has been disconnected due to inactivity.")
            reset_game()

# Periodically check for inactive players
def periodic_check():
    while True:
        time.sleep(10)  # Every 10 seconds, check for inactivity
        check_inactive_players()

# Start the periodic check in a background thread
threading.Thread(target=periodic_check, daemon=True).start()

# Handle player making a move
@app.route("/make_move", methods=["POST"])
def make_move():
    data = request.get_json()
    symbol = data["symbol"]
    index = data["index"]
    
    if game_state["board"][index] != "":
        return jsonify({"success": False, "message": "Invalid move"}), 400

    game_state["board"][index] = symbol
    game_state["last_activity"][symbol] = time.time()  # Update the last activity time for the player

    # Check for winner
    winner = check_winner()
    if winner:
        game_state["winner"] = winner
    else:
        # Change turn
        game_state["current_turn"] = "X" if symbol == "O" else "O"
    
    return jsonify({"success": True})

# Check if there's a winner
def check_winner():
    win_conditions = [(0, 1, 2), (3, 4, 5), (6, 7, 8), (0, 3, 6), (1, 4, 7), (2, 5, 8), (0, 4, 8), (2, 4, 6)]
    for condition in win_conditions:
        a, b, c = condition
        if game_state["board"][a] == game_state["board"][b] == game_state["board"][c] != "":
            return game_state["board"][a]  # Return the symbol (X or O) of the winner
    return None

# Get the current game state
@app.route("/get_state", methods=["GET"])
def get_state():
    return jsonify(game_state)

# Reset the game
@app.route("/reset", methods=["POST"])
def reset_game():
    game_state["board"] = [""] * 9
    game_state["winner"] = None
    game_state["current_turn"] = "X"
    game_state["last_activity"] = {"X": time.time(), "O": time.time()}  # Reset activity times
    return jsonify({"success": True})

# Serve the main game page (HTML)
@app.route("/")
def index():
    return render_template("index.html")  # This will render index.html located in the templates folder

# Run the Flask app
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
