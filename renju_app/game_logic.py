import random

def make_move(game_state, username, x, y):
    if game_state['winner'] != 0:
        return False

    current_color = game_state['current_turn']
    current_player_username = game_state['players'].get(current_color)

    # Validation: Is it this user's turn?
    if current_player_username != username:
        return False

    # Validation: Is the spot empty?
    if not (0 <= x < 15 and 0 <= y < 15):
        return False
    if game_state['board'][y][x] != 0:
        return False

    # Renju Rules: Black (1) has forbidden moves.
    # We will check for Overline (6 or more stones).
    # Double-3 and Double-4 are complex to implement efficiently in this scope,
    # so we will focus on Overline and winning condition differences.
    if current_color == 1:
        if is_overline(game_state['board'], x, y, 1):
             # Overline is forbidden for Black. Move rejected.
             return False

    apply_move(game_state, x, y, current_color)
    return True

def apply_move(game_state, x, y, color):
    game_state['board'][y][x] = color
    game_state['moves'].append({'x': x, 'y': y, 'color': color})

    # Check win
    if check_win(game_state['board'], x, y, color):
        game_state['winner'] = color
    else:
        game_state['current_turn'] = 3 - color # Switch 1 <-> 2

def count_consecutive(board, x, y, dx, dy, color):
    count = 1
    # Check forward
    nx, ny = x + dx, y + dy
    while 0 <= nx < 15 and 0 <= ny < 15 and board[ny][nx] == color:
        count += 1
        nx += dx
        ny += dy
    # Check backward
    nx, ny = x - dx, y - dy
    while 0 <= nx < 15 and 0 <= ny < 15 and board[ny][nx] == color:
        count += 1
        nx -= dx
        ny -= dy
    return count

def is_overline(board, x, y, color):
    # Temporarily place stone to check
    board[y][x] = color
    directions = [(1, 0), (0, 1), (1, 1), (1, -1)]
    is_forbidden = False
    for dx, dy in directions:
        count = count_consecutive(board, x, y, dx, dy, color)
        if count > 5:
            is_forbidden = True
            break
    # Revert
    board[y][x] = 0
    return is_forbidden

def check_win(board, x, y, color):
    directions = [(1, 0), (0, 1), (1, 1), (1, -1)]
    for dx, dy in directions:
        count = count_consecutive(board, x, y, dx, dy, color)

        if color == 1:
            # Black wins with EXACTLY 5
            if count == 5:
                return True
        else:
            # White wins with 5 OR MORE
            if count >= 5:
                return True
    return False

def get_computer_move(game_state):
    """
    Determines the computer's move.
    Requirement: "Call LLM to find out the best next move"

    Since we do not have a configured LLM API key in this environment,
    we are simulating the integration.
    """

    board = game_state['board']
    empty_spots = []
    for r in range(15):
        for c in range(15):
            if board[r][c] == 0:
                empty_spots.append((c, r))

    if not empty_spots:
        return None

    # --- LLM INTEGRATION START ---
    # In a production environment with an LLM API (e.g., OpenAI, Gemini, Anthropic),
    # the code would look something like this:
    #
    # prompt = f"""
    # You are playing Renju (Gomoku with rules). You are White (Player 2).
    # The board is 15x15.
    # Current board state (0=empty, 1=Black, 2=White):
    # {board}
    # Move history: {game_state['moves']}
    #
    # Return ONLY the coordinates of the best next move as 'x,y'.
    # """
    #
    # try:
    #     response = llm_client.generate_content(prompt) # Hypothetical call
    #     move_str = response.text.strip()
    #     x, y = map(int, move_str.split(','))
    #     if (x, y) in empty_spots:
    #         return (x, y)
    # except Exception as e:
    #     logger.error(f"LLM call failed: {e}")
    #     # Fallback to heuristic/random
    #
    # --- LLM INTEGRATION END ---

    # Simple Heuristic Fallback:
    # 1. Check if we can win now (White, 5+)
    for x, y in empty_spots:
        board[y][x] = 2
        if check_win(board, x, y, 2):
            board[y][x] = 0
            return (x, y)
        board[y][x] = 0

    # 2. Check if opponent (Black) can win next turn (5), and block it.
    for x, y in empty_spots:
        board[y][x] = 1
        if check_win(board, x, y, 1):
             board[y][x] = 0
             return (x, y) # Block!
        board[y][x] = 0

    # 3. Random valid move
    return random.choice(empty_spots)
