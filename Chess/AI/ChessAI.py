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

def load_book_moves():
    """Loads book moves from Book.txt in the new format."""
    current_fen = None
    with open("Chess/AI/Book.txt", "r") as file:
        for line in file:
            line = line.strip()
            if line.startswith("pos"):  # New FEN position
                _, current_fen = line.split(" ", 1)
                book_moves[current_fen] = []  # Initialize empty list for the FEN
            else:
                move, count = line.split()  # Extract move and its frequency
                count = int(count)  # Convert count to integer
                book_moves[current_fen].append((move, count))  # Store (move, count) as a tuple

load_book_moves()  # Load book moves at the start

def get_random_book_move(fen):
    """Returns a random book move using weighted randomness based on frequency."""
    if fen not in book_moves:
        return None  # No book move available for this FEN

    moves_with_counts = book_moves[fen]
    moves, counts = zip(*moves_with_counts)  # Unpack moves and counts
    total_count = sum(counts)

    # Normalize counts to probabilities
    probabilities = [count / total_count for count in counts]

    # Shuffle the move list to prevent predictable results for same-weight moves
    move_and_probabilities = list(zip(moves, probabilities))
    random.shuffle(move_and_probabilities)
    moves, probabilities = zip(*move_and_probabilities)

    # Weighted random choice of move based on frequencies
    chosen_move = random.choices(moves, weights=probabilities, k=1)[0]
    return chosen_move

def score_move(move):
    """Assign a score to a move based on capture and piece value."""
    if move.piece_captured != '--':
        return piece_values.get(move.piece_captured, 0)
    return 0  # Non-captures have a lower priority

def find_best_move_from_fen(game_state):
    """Reads FEN, generates valid moves, and finds the best move."""
    fen = game_state.get_fen()  # Get FEN from your GameState class
    book_move = get_random_book_move(fen)  # Get a random weighted book move

    if book_move:
        print(f"Playing book move: {book_move}")
        return book_move, 0, 0  # No depth or evaluation for book move

    # If no book move, fallback to AI move
    valid_moves = game_state.get_valid_moves()

    if not valid_moves:
        return None, 0, 0  # No valid moves available

    best_move, depth_reached, eval_score = find_best_move(game_state, valid_moves)
    return best_move, depth_reached, eval_score

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
