document.addEventListener('DOMContentLoaded', () => {
    const socket = io();

    // UI Elements
    const loginScreen = document.getElementById('login-screen');
    const lobbyScreen = document.getElementById('lobby-screen');
    const gameScreen = document.getElementById('game-screen');

    const usernameInput = document.getElementById('username');
    const loginBtn = document.getElementById('login-btn');
    const displayUsername = document.getElementById('display-username');

    const roomNameInput = document.getElementById('room-name');
    const gameTypeSelect = document.getElementById('game-type');
    const createRoomBtn = document.getElementById('create-room-btn');
    const roomList = document.getElementById('room-list');

    const board = document.getElementById('board');
    const moveHistory = document.getElementById('move-history');
    const gameStatus = document.getElementById('game-status');
    const leaveRoomBtn = document.getElementById('leave-room-btn');
    const roomTitle = document.getElementById('room-title');

    let currentRoomId = null;
    let myRole = null; // 'player' or 'spectator'
    let myColor = null; // 1 (Black) or 2 (White) - only if player

    // Login
    loginBtn.addEventListener('click', () => {
        const username = usernameInput.value;
        if (username) {
            socket.emit('login', { username: username });
        }
    });

    socket.on('login_success', (data) => {
        loginScreen.style.display = 'none';
        lobbyScreen.style.display = 'block';
        displayUsername.textContent = data.username;
    });

    // Lobby
    socket.on('update_lobby', (rooms) => {
        roomList.innerHTML = '';
        rooms.forEach(room => {
            const li = document.createElement('li');
            li.textContent = `${room.name} (${room.type}) - Players: ${room.players}/2`;
            const joinBtn = document.createElement('button');
            joinBtn.textContent = 'Join';
            joinBtn.onclick = () => {
                socket.emit('join_room', { room_id: room.id });
            };
            li.appendChild(joinBtn);
            roomList.appendChild(li);
        });
    });

    createRoomBtn.addEventListener('click', () => {
        const roomName = roomNameInput.value;
        const gameType = gameTypeSelect.value;
        if (roomName) {
            socket.emit('create_room', { room_name: roomName, game_type: gameType });
        }
    });

    socket.on('room_joined', (data) => {
        currentRoomId = data.room_id;
        myRole = data.role;
        // In this simple implementation, creator is always Black (1) initially if PvP
        // If joining existing room, server assigns.
        // We need to wait for full state to know our color, actually.
        // But simply, if we created it, we are player 1. If we joined and there's already 1 player, we are 2.

        lobbyScreen.style.display = 'none';
        gameScreen.style.display = 'block';

        // Render empty board
        renderBoard([]);
    });

    leaveRoomBtn.addEventListener('click', () => {
        // Reload for now to reset state
        window.location.reload();
    });

    // Game
    socket.on('update_room_state', (gameState) => {
        renderBoard(gameState.board);
        updateHistory(gameState.moves);
        updateStatus(gameState);

        // Determine my color
        const myUsername = displayUsername.textContent;
        if (gameState.players[1] === myUsername) {
            myColor = 1;
        } else if (gameState.players[2] === myUsername) {
            myColor = 2;
        } else {
            myColor = null; // Spectator
        }
    });

    function renderBoard(boardData) {
        board.innerHTML = '';
        for (let y = 0; y < 15; y++) {
            for (let x = 0; x < 15; x++) {
                const cell = document.createElement('div');
                cell.className = 'cell';
                cell.dataset.x = x;
                cell.dataset.y = y;

                cell.addEventListener('click', () => {
                    if (myRole === 'player' && currentRoomId) {
                        socket.emit('make_move', { room_id: currentRoomId, x: x, y: y });
                    }
                });

                if (boardData && boardData[y] && boardData[y][x] !== 0) {
                    const stone = document.createElement('div');
                    stone.className = `stone ${boardData[y][x] === 1 ? 'black' : 'white'}`;
                    cell.appendChild(stone);
                }

                board.appendChild(cell);
            }
        }
    }

    function updateHistory(moves) {
        moveHistory.innerHTML = '';
        moves.forEach((move, index) => {
            const li = document.createElement('li');
            const color = move.color === 1 ? 'Black' : 'White';
            // Convert to chess-like notation (e.g., H8) or just coords
            const colChar = String.fromCharCode(65 + move.x); // A, B, C...
            const rowNum = 15 - move.y;
            li.textContent = `${index + 1}. ${color}: ${colChar}${rowNum}`;
            moveHistory.appendChild(li);
        });
    }

    function updateStatus(gameState) {
        let statusText = '';
        if (gameState.winner !== 0) {
            const winner = gameState.winner === 1 ? 'Black' : 'White';
            statusText = `Game Over! Winner: ${winner}`;
        } else {
            const turn = gameState.current_turn === 1 ? 'Black' : 'White';
            statusText = `Current Turn: ${turn}`;
            if (myColor && gameState.current_turn === myColor) {
                statusText += " (Your Turn)";
            }
        }
        gameStatus.textContent = statusText;
    }
});
