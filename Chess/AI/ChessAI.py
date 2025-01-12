from AI.evaluation import score_board
import random

checkmate_points = 100000  # 1000 points as centipawns (multiplied by 100)
set_depth = 4  # Search depth for Negamax

# Dictionary to store book moves {FEN: [(move, count), (move, count), ...]}
book_moves = {}

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

    # Weighted random choice of move based on frequencies
    chosen_move = random.choices(moves, weights=probabilities, k=1)[0]
    return chosen_move

def find_best_move_from_fen(game_state):
    """Reads FEN, generates valid moves, and finds the best move."""
    fen = game_state.get_fen()  # Get FEN from your GameState class
    book_move = get_random_book_move(fen)  # Get a random weighted book move
    
    if book_move:
        print(f"Playing book move: {book_move}")
        return book_move  # Play a random weighted book move

    # If no book move, fallback to AI move
    valid_moves = game_state.get_valid_moves()
    best_move = find_best_move(game_state, valid_moves)
    return best_move

def find_best_move(game_state, valid_moves):
    """Find the best move using Negamax with Alpha-Beta pruning."""
    global next_move
    next_move = None
    find_negamax_move_alphabeta(game_state, valid_moves, set_depth, -checkmate_points, checkmate_points,
                                1 if game_state.white_to_move else -1)
    return next_move

def find_negamax_move_alphabeta(game_state, valid_moves, depth, alpha, beta, turn_multiplier):
    """Negamax algorithm with alpha-beta pruning."""
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
                next_move = move

        # Alpha-beta pruning
        alpha = max(alpha, max_score)
        if alpha >= beta:
            break

    return max_score
