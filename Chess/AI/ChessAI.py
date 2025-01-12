# Import piece-square tables and piece values from piece_square_table.py
from AI.piece_square_table import piece_square_tables, piece_values

# Depth of the algorithm determining AI moves. Higher set_depth == harder AI.
set_depth = 4

# Points for game outcome (in centipawns).
checkmate_points = 100000  # 1000 points as centipawns (multiplied by 100)
stalemate_points = 0

# ------------------------------------------------------------------
# Function to find the best move based on the current board state.
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
    """Evaluates the board to return a score using PeSTO's evaluation."""
    if game_state.checkmate:
        if game_state.white_to_move:
            return -checkmate_points  # Black wins
        else:
            return checkmate_points  # White wins
    elif game_state.stalemate:
        return stalemate_points

    mg_score, eg_score = 0, 0
    phase = 0  # Game phase indicator for tapering

    for row in range(8):
        for col in range(8):
            piece = game_state.board[row][col]
            if piece != '--':  # Ignore empty squares
                piece_type = piece[1].upper()  # 'P', 'N', etc.
                color = 'w' if piece[0] == 'w' else 'b'
                index = row * 8 + col  # Convert 2D board index to 1D

                if color == 'w':
                    mg_score += piece_values[piece_type][0] + piece_square_tables['mg'][piece_type][index]
                    eg_score += piece_values[piece_type][1] + piece_square_tables['eg'][piece_type][index]
                    phase += 1 if piece_type not in ["P", "K"] else 0  # Add phase for non-pawns
                else:
                    mg_score -= piece_values[piece_type][0] + piece_square_tables['mg'][piece_type][63 - index]
                    eg_score -= piece_values[piece_type][1] + piece_square_tables['eg'][piece_type][63 - index]
                    phase += 1 if piece_type not in ["P", "K"] else 0  # Add phase for non-pawns

    # Tapered evaluation between midgame and endgame
    mg_phase = min(phase, 24)  # Midgame phase indicator (max 24)
    eg_phase = 24 - mg_phase  # Endgame phase is inverse of midgame phase

    # Weighted average of midgame and endgame scores
    return (mg_score * mg_phase + eg_score * eg_phase) // 24