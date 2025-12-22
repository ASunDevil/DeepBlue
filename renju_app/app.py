from flask import Flask, render_template, request, session
from flask_socketio import SocketIO, emit, join_room, leave_room
import logging

app = Flask(__name__)
app.config['SECRET_KEY'] = 'renju-secret!'
socketio = SocketIO(app, async_mode='eventlet', cors_allowed_origins='*')

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Store lobby and game data in memory
users = {} # session_id -> username
rooms = {} # room_id -> {id: str, name: str, players: [username1, username2], spectators: [username], game_state: ...}
# game_state structure:
# {
#   board: 15x15 list of lists (0: empty, 1: black, 2: white),
#   current_turn: 1 (black) or 2 (white),
#   winner: 0 (none), 1, or 2,
#   moves: list of {x: int, y: int, color: int},
#   players: {1: username_black, 2: username_white}
# }

import lobby
import game_logic

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('connect')
def on_connect():
    logger.info(f'Client connected: {request.sid}')

@socketio.on('disconnect')
def on_disconnect():
    username = users.get(request.sid)
    if username:
        del users[request.sid]
        # Handle cleanup if needed, e.g., leave rooms
        lobby.handle_user_disconnect(username, rooms, socketio)
    logger.info(f'Client disconnected: {request.sid}')

@socketio.on('login')
def on_login(data):
    username = data.get('username')
    if not username:
        return
    users[request.sid] = username
    emit('login_success', {'username': username})
    emit('update_lobby', lobby.get_lobby_info(rooms), broadcast=True)

@socketio.on('create_room')
def on_create_room(data):
    username = users.get(request.sid)
    room_name = data.get('room_name')
    game_type = data.get('game_type') # 'pvp' or 'pvc'

    if username and room_name:
        room_id = lobby.create_room(username, room_name, game_type, rooms)
        join_room(room_id)
        emit('room_joined', {'room_id': room_id, 'game_type': game_type, 'role': 'player'})
        emit('update_lobby', lobby.get_lobby_info(rooms), broadcast=True)

@socketio.on('join_room')
def on_join_room(data):
    username = users.get(request.sid)
    room_id = data.get('room_id')

    if username and room_id in rooms:
        success, role = lobby.join_room(username, room_id, rooms)
        if success:
            join_room(room_id)
            emit('room_joined', {'room_id': room_id, 'game_type': rooms[room_id]['type'], 'role': role})
            emit('update_room_state', rooms[room_id]['game_state'], to=room_id)
            emit('update_lobby', lobby.get_lobby_info(rooms), broadcast=True)

@socketio.on('make_move')
def on_make_move(data):
    username = users.get(request.sid)
    room_id = data.get('room_id')
    x = data.get('x')
    y = data.get('y')

    if username and room_id in rooms:
        game_state = rooms[room_id]['game_state']
        if game_logic.make_move(game_state, username, x, y):
             emit('update_room_state', game_state, to=room_id)

             # Check if computer needs to move
             if rooms[room_id]['type'] == 'pvc' and game_state['winner'] == 0:
                 current_player_color = game_state['current_turn']
                 # Assuming computer is always White (2) for now or handles the turn
                 computer_color = 2
                 if current_player_color == computer_color:
                     computer_move = game_logic.get_computer_move(game_state)
                     if computer_move:
                         game_logic.apply_move(game_state, computer_move[0], computer_move[1], computer_color)
                         emit('update_room_state', game_state, to=room_id)

if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)
