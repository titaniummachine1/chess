
# Depth of the algorithm determining AI moves. Higher set_depth == harder AI.
set_depth = 4

# Points for game outcome.
checkmate_points = 1000
stalemate_points = 0

piece_scores = {'K': 200.0, 'Q': 9.0, 'R': 5.0, 'B': 3.3, 'N': 3.2, 'P': 1.0}

piece_positions = {
    'wP': [  # White pawns
        [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
        [5.0, 5.0, 5.0, 5.0, 5.0, 5.0, 5.0, 5.0],
        [1.0, 1.0, 2.0, 3.0, 3.0, 2.0, 1.0, 1.0],
        [0.5, 0.5, 1.0, 2.5, 2.5, 1.0, 0.5, 0.5],
        [0.0, 0.0, 0.0, 2.0, 2.0, 0.0, 0.0, 0.0],
        [0.5, -0.5, -1.0, 0.0, 0.0, -1.0, -0.5, 0.5],
        [0.5, 1.0, 1.0, -2.0, -2.0, 1.0, 1.0, 0.5],
        [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]],
    'bP': [  # Black pawns
        [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
        [0.5, 1.0, 1.0, -2.0, -2.0, 1.0, 1.0, 0.5],
        [0.5, -0.5, -1.0, 0.0, 0.0, -1.0, -0.5, 0.5],
        [0.0, 0.0, 0.0, 2.0, 2.0, 0.0, 0.0, 0.0],
        [0.5, 0.5, 1.0, 2.5, 2.5, 1.0, 0.5, 0.5],
        [1.0, 1.0, 2.0, 3.0, 3.0, 2.0, 1.0, 1.0],
        [5.0, 5.0, 5.0, 5.0, 5.0, 5.0, 5.0, 5.0],
        [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]],
    # Position tables for other pieces can be added here...
}

# ------------------------------------------------------------------
# Function to find the best move based on current board state.
# ------------------------------------------------------------------
def find_best_move(game_state, valid_moves):
    """Find the best move using Negamax with Alpha-Beta pruning."""
    global next_move
    next_move = None
    find_negamax_move_alphabeta(game_state, valid_moves, set_depth, -checkmate_points, checkmate_points,
                                1 if game_state.white_to_move else -1)
    return next_move


def find_negamax_move_alphabeta(game_state, valid_moves, depth, alpha, beta, turn_multiplier):
    """
    Negamax algorithm with alpha-beta pruning.
    turn_multiplier: 1 for white, -1 for black.
    """
    global next_move

    if depth == 0:
        return turn_multiplier * score_board(game_state)

    max_score = -checkmate_points
    for move in valid_moves:
        game_state.make_move(move)
        next_moves = game_state.get_valid_moves()
        score = -find_negamax_move_alphabeta(game_state, next_moves, depth - 1, -beta, -alpha, -turn_multiplier)
        game_state.undo_move()

        if score > max_score:
            max_score = score
            if depth == set_depth:
                next_move = move  # Store the best move at the root level.

        # Alpha-beta pruning
        alpha = max(alpha, max_score)
        if alpha >= beta:
            break

    return max_score


# ------------------------------------------------------------------
# Board Evaluation Function
# ------------------------------------------------------------------
def score_board(game_state):
    """Evaluates the board to return a score."""
    if game_state.checkmate:
        if game_state.white_to_move:
            return -checkmate_points  # Black wins
        else:
            return checkmate_points  # White wins
    elif game_state.stalemate:
        return stalemate_points

    score = 0
    for row in range(8):
        for col in range(8):
            piece = game_state.board[row][col]
            if piece != '--':  # Ignore empty squares
                piece_value = piece_scores.get(piece[1], 0)
                if piece[0] == 'w':
                    score += piece_value + piece_positions.get(piece, [[0] * 8 for _ in range(8)])[row][col]
                else:
                    score -= piece_value + piece_positions.get(piece, [[0] * 8 for _ in range(8)])[row][col]
    return score
