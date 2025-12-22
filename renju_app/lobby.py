import uuid

def get_lobby_info(rooms):
    lobby_data = []
    for r_id, r in rooms.items():
        lobby_data.append({
            'id': r_id,
            'name': r['name'],
            'type': r['type'],
            'players': len(r['players']),
            'spectators': len(r['spectators'])
        })
    return lobby_data

def create_room(username, room_name, game_type, rooms):
    room_id = str(uuid.uuid4())
    rooms[room_id] = {
        'id': room_id,
        'name': room_name,
        'type': game_type,
        'players': [username],
        'spectators': [],
        'game_state': {
            'board': [[0]*15 for _ in range(15)],
            'current_turn': 1, # 1: Black, 2: White
            'winner': 0,
            'moves': [],
            'players': {1: username, 2: 'Computer' if game_type == 'pvc' else None}
        }
    }
    return room_id

def join_room(username, room_id, rooms):
    room = rooms.get(room_id)
    if not room:
        return False, None

    if username in room['players']:
        return True, 'player'

    if len(room['players']) < 2 and room['type'] == 'pvp':
        room['players'].append(username)
        room['game_state']['players'][2] = username
        return True, 'player'

    if username not in room['spectators']:
        room['spectators'].append(username)
    return True, 'spectator'

def handle_user_disconnect(username, rooms, socketio):
    # Remove user from rooms?
    # For now, maybe just keep them until the game is over or timeouts
    pass
