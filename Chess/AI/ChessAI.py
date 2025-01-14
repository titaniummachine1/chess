from AI.evaluation import score_board, piece_values
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

# Function to score moves based on checks, captures, and material (MVV-LVA)
def score_move(move, game_state):
    """
    Assign a score to a move:
    - High score for checks
    - MVV-LVA for captures (victim vs attacker)
    - Penalty for pawn moves unless promoting or critical center
    """
    score = 0

    # Check if the move is a check
    game_state.make_move(move)
    is_check = game_state.in_check  # Check if the king is under attack after the move
    game_state.undo_move()

    if is_check:
        score += 10000  # High score for moves that put the opponent in check

    # If it's a capture, apply MVV-LVA logic
    if move.piece_captured != '--':
        victim_value = piece_values.get(move.piece_captured[1].upper(), (0, 0))[0]  # Midgame value
        attacker_value = piece_values.get(move.piece_moved[1].upper(), (0, 0))[0]  # Midgame value
        score += (victim_value * 10 - attacker_value)

    # Small penalty for non-piece moves (prioritize moving pieces over pawns)
    if move.piece_moved[1].upper() == 'P':  # If it's a pawn move
        score -= 10  # Penalize non-promotion pawn moves slightly

    return score

# Iterative deepening with minimax and alpha-beta pruning
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

    # Sort moves based on their improved scoring function
    sorted_moves = sorted(valid_moves, key=lambda move: score_move(move, game_state), reverse=True)

    if maximizing_player:
        max_eval = -checkmate_points
        for move in sorted_moves:
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
        for move in sorted_moves:
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