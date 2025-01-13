# AI/ChessAI.py

from AI.evaluation import score_board
import random
import threading  # To use threading.Lock if not already imported

checkmate_points = 100000  # 1000 points as centipawns (multiplied by 100)
set_depth = 4  # Max depth for iterative deepening

# Dictionary to store book moves {FEN: [(move, count), (move, count), ...]}
book_moves = {}

# Global variables for GUI to access
current_depth = 0  # The current depth being evaluated
current_evaluation = 0  # The evaluation score at the current depth
positions_analyzed = 0  # Number of positions analyzed
best_move_found = None  # Best move found so far

# Initialize a lock for thread-safe operations
lock = threading.Lock()

# Initialize the stop_analysis flag
stop_analysis = False

# Define piece values (in centipawns)
piece_values = {
    'wP': 100,
    'bP': 100,
    'wN': 320,
    'bN': 320,
    'wB': 330,
    'bB': 330,
    'wR': 500,
    'bR': 500,
    'wQ': 900,
    'bQ': 900,
    'wK': 0,   # King is invaluable; not typically captured
    'bK': 0
}

def score_move(move):
    """Assign a score to a move based on capture and piece value."""
    if move.piece_captured != '--':
        return piece_values.get(move.piece_captured, 0)
    return 0  # Non-captures have a lower priority

def find_best_move(game_state, valid_moves):
    """Find the best move using iterative deepening with Negamax and Alpha-Beta pruning."""
    global current_depth, current_evaluation, positions_analyzed, best_move_found, stop_analysis
    best_move_found = None

    # Iterative deepening loop
    for depth in range(1, set_depth + 1):
        with lock:
            if stop_analysis:
                print("AI analysis stopped by user.")
                break
            current_depth = depth  # Update the current depth

        current_evaluation = find_negamax_move_alphabeta(game_state, valid_moves, depth, -checkmate_points,
                                                         checkmate_points, 1 if game_state.white_to_move else -1)

    return best_move_found, current_depth, current_evaluation

def find_negamax_move_alphabeta(game_state, valid_moves, depth, alpha, beta, turn_multiplier):
    """Negamax algorithm with alpha-beta pruning and move ordering."""
    global best_move_found, current_evaluation, positions_analyzed, stop_analysis

    if depth == 0:
        evaluation = turn_multiplier * score_board(game_state)
        with lock:
            current_evaluation = evaluation  # Update evaluation at leaf nodes
            positions_analyzed += 1  # Increment positions analyzed
        return evaluation

    max_score = -checkmate_points
    # Sort moves based on their score in descending order
    sorted_moves = sorted(valid_moves, key=lambda move: score_move(move), reverse=True)

    for move in sorted_moves:
        with lock:
            if stop_analysis:
                return 0  # Early termination

        game_state.make_move(move)
        next_moves = game_state.get_valid_moves()
        score = -find_negamax_move_alphabeta(game_state, next_moves, depth - 1, -beta, -alpha, -turn_multiplier)
        game_state.undo_move()

        if score > max_score:
            max_score = score
            if depth == current_depth:  # Only update the best move at the current search depth
                best_move_found = move

        alpha = max(alpha, max_score)
        if alpha >= beta:
            break  # Beta cutoff

    with lock:
        positions_analyzed += 1  # Increment positions analyzed
    return max_score
