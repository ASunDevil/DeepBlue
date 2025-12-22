import socketio
import time
import sys

# Client 1
sio1 = socketio.Client()
sio2 = socketio.Client()
sio3 = socketio.Client()

room_id_1 = None

@sio1.event
def connect():
    print("Client 1 connected")

@sio1.event
def login_success(data):
    print(f"Client 1 logged in as {data['username']}")

@sio1.event
def room_joined(data):
    global room_id_1
    print(f"Client 1 joined room {data['room_id']}")
    room_id_1 = data['room_id']

@sio1.event
def update_room_state(data):
    print(f"Client 1 received board update. Last move: {data['moves'][-1] if data['moves'] else 'Start'}")

@sio2.event
def connect():
    print("Client 2 connected")

@sio2.event
def login_success(data):
    print(f"Client 2 logged in as {data['username']}")

@sio2.event
def room_joined(data):
    print(f"Client 2 joined room {data['room_id']}")

@sio3.event
def connect():
    print("Client 3 connected")

@sio3.event
def update_room_state(data):
    print(f"Client 3 received board update. Last move: {data['moves'][-1] if data['moves'] else 'Start'}")
    if data['moves'] and data['moves'][-1]['color'] == 2:
        print("Computer made a move!")

def test_pvp():
    print("--- Testing PvP ---")
    sio1.connect('http://localhost:5000')
    sio1.emit('login', {'username': 'Player1'})
    time.sleep(1)

    sio1.emit('create_room', {'room_name': 'Room1', 'game_type': 'pvp'})
    time.sleep(1)

    if not room_id_1:
        print("Failed to create room")
        return

    sio2.connect('http://localhost:5000')
    sio2.emit('login', {'username': 'Player2'})
    time.sleep(1)

    sio2.emit('join_room', {'room_id': room_id_1})
    time.sleep(1)

    # Player 1 moves (Black)
    print("Player 1 moving to 7,7")
    sio1.emit('make_move', {'room_id': room_id_1, 'x': 7, 'y': 7})
    time.sleep(1)

    # Player 2 moves (White)
    print("Player 2 moving to 7,8")
    sio2.emit('make_move', {'room_id': room_id_1, 'x': 7, 'y': 8})
    time.sleep(1)

    sio1.disconnect()
    sio2.disconnect()

def test_pvc():
    print("\n--- Testing PvC ---")
    sio3.connect('http://localhost:5000')
    sio3.emit('login', {'username': 'Player3'})
    time.sleep(1)

    sio3.emit('create_room', {'room_name': 'RoomAI', 'game_type': 'pvc'})
    time.sleep(1)

    # We need to capture the room ID for Client 3.
    # Since I didn't set a global for it, I'll rely on the assumption that create_room automatically joins the creator.
    # But I need the room ID to send moves.
    # I should have added a handler for room_joined on sio3.
    pass

# Helper to capture room id for sio3
room_id_3 = None
@sio3.event
def room_joined(data):
    global room_id_3
    print(f"Client 3 joined room {data['room_id']}")
    room_id_3 = data['room_id']

def run_tests():
    try:
        test_pvp()

        # Reset specific vars for next test if needed
        # Run PvC
        print("\n--- Testing PvC ---")
        sio3.connect('http://localhost:5000')
        sio3.emit('login', {'username': 'Player3'})
        time.sleep(1)
        sio3.emit('create_room', {'room_name': 'RoomAI', 'game_type': 'pvc'})
        time.sleep(1)

        if room_id_3:
            print("Player 3 moving to 7,7")
            sio3.emit('make_move', {'room_id': room_id_3, 'x': 7, 'y': 7})
            time.sleep(2) # Wait for computer response
        else:
            print("Failed to create AI room")

        sio3.disconnect()

    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    run_tests()
