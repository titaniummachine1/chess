from AI.evaluation import score_board
import random
import threading  # To use threading.Lock for thread safety

checkmate_points = 100000  # Checkmate points as centipawns
set_depth = 4  # Maximum search depth for the AI

# Global variables for GUI to access
current_depth = 0  # The current search depth being evaluated
current_evaluation = 0  # The evaluation score of the best move found so far
positions_analyzed = 0  # Number of board positions analyzed
best_move_found = None  # Best move found during the search

# Lock for thread-safe operations
lock = threading.Lock()

# Stop analysis flag
stop_analysis = False

# Piece values for scoring (in centipawns)
piece_values = {
    'wP': 100,  # White pawn
    'bP': 100,  # Black pawn
    'wN': 320,  # White knight
    'bN': 320,  # Black knight
    'wB': 330,  # White bishop
    'bB': 330,  # Black bishop
    'wR': 500,  # White rook
    'bR': 500,  # Black rook
    'wQ': 900,  # White queen
    'bQ': 900,  # Black queen
    'wK': 0,    # White king (invaluable)
    'bK': 0     # Black king (invaluable)
}

# Function to score moves based on Most Valuable Victim-Least Valuable Attacker (MVV-LVA)
def score_move(move):
    """Assign a score to a move based on MVV-LVA."""
    if move.piece_captured != '--':  # If a piece is captured
        victim_value = piece_values.get(move.piece_captured, 0)
        attacker_value = piece_values.get(move.piece_moved, 0)
        return victim_value * 10 - attacker_value  # Prioritize capturing valuable pieces
    return 0  # Non-capturing moves have lower priority

# Iterative deepening with minimax search
def find_best_move(game_state, valid_moves):
    """Find the best move using minimax with alpha-beta pruning."""
    global current_depth, current_evaluation, positions_analyzed, best_move_found, stop_analysis
    best_move_found = None
    best_evaluation_so_far = -checkmate_points if game_state.white_to_move else checkmate_points

    for depth in range(1, set_depth + 1):
        with lock:
            if stop_analysis:
                print("AI analysis stopped by user.")
                break
            current_depth = depth  # Update the current search depth

        if game_state.white_to_move:
            evaluation = minimax_with_alpha_beta(game_state, valid_moves, depth, True, -checkmate_points, checkmate_points)
        else:
            evaluation = minimax_with_alpha_beta(game_state, valid_moves, depth, False, -checkmate_points, checkmate_points)

        # Update the evaluation score after completing the current depth
        current_evaluation = evaluation

    return best_move_found, current_depth, current_evaluation

def minimax_with_alpha_beta(game_state, valid_moves, depth, maximizing_player, alpha, beta):
    """Minimax algorithm with alpha-beta pruning."""
    global best_move_found, positions_analyzed, stop_analysis

    if depth == 0:
        evaluation = score_board(game_state)  # Evaluate the board at depth 0
        with lock:
            positions_analyzed += 1  # Count analyzed positions
        return evaluation

    if maximizing_player:
        max_eval = -checkmate_points
        for move in sorted(valid_moves, key=score_move, reverse=True):  # Sort moves by MVV-LVA for better pruning
            with lock:
                if stop_analysis:
                    return 0

            game_state.make_move(move)
            next_moves = game_state.get_valid_moves()
            evaluation = minimax_with_alpha_beta(game_state, next_moves, depth - 1, False, alpha, beta)
            game_state.undo_move()

            if evaluation > max_eval:
                max_eval = evaluation
                if depth == current_depth:
                    best_move_found = move  # Update best move only at the current search depth

            alpha = max(alpha, max_eval)
            if alpha >= beta:
                break  # Beta cutoff

        return max_eval

    else:
        min_eval = checkmate_points
        for move in sorted(valid_moves, key=score_move, reverse=True):
            with lock:
                if stop_analysis:
                    return 0

            game_state.make_move(move)
            next_moves = game_state.get_valid_moves()
            evaluation = minimax_with_alpha_beta(game_state, next_moves, depth - 1, True, alpha, beta)
            game_state.undo_move()

            if evaluation < min_eval:
                min_eval = evaluation
                if depth == current_depth:
                    best_move_found = move

            beta = min(beta, min_eval)
            if beta <= alpha:
                break  # Alpha cutoff

        return min_eval