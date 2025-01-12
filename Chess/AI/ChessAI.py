from AI.evaluation import score_board
import random
import time  # To track the time taken for each depth

checkmate_points = 100000  # 1000 points as centipawns (multiplied by 100)
set_depth = 4  # Max depth for iterative deepening

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

    # Shuffle the move list to prevent predictable results for same-weight moves
    move_and_probabilities = list(zip(moves, probabilities))
    random.shuffle(move_and_probabilities)
    moves, probabilities = zip(*move_and_probabilities)

    # Weighted random choice of move based on frequencies
    chosen_move = random.choices(moves, weights=probabilities, k=1)[0]
    return chosen_move

def find_random_move(valid_moves):
    """Returns a completely random move from the list of valid moves."""
    if not valid_moves:
        return None  # No valid moves
    return random.choice(valid_moves)

def find_best_move_from_fen(game_state):
    """Reads FEN, generates valid moves, and finds the best move."""
    fen = game_state.get_fen()  # Get FEN from your GameState class
    book_move = get_random_book_move(fen)  # Get a random weighted book move
    
    if book_move:
        print(f"Playing book move: {book_move}")
        return book_move, 0, 0  # No depth or evaluation for book move

    # If no book move, fallback to AI move
    valid_moves = game_state.get_valid_moves()

    # Example of fallback to random move if no calculated move
    if not valid_moves:
        return None, 0, 0
    best_move, depth_reached, eval_score = find_best_move(game_state, valid_moves)
    return best_move, depth_reached, eval_score

def find_best_move(game_state, valid_moves):
    """Find the best move using iterative deepening with Negamax and Alpha-Beta pruning."""
    global next_move
    next_move = None
    eval_score = 0

    # Iterative deepening from depth 1 to set_depth
    for depth in range(1, set_depth + 1):
        eval_score = find_negamax_move_alphabeta(game_state, valid_moves, depth, -checkmate_points, checkmate_points,
                                                 1 if game_state.white_to_move else -1)

    return next_move, depth, eval_score

def find_negamax_move_alphabeta(game_state, valid_moves, depth, alpha, beta, turn_multiplier):
    """Negamax algorithm with alpha-beta pruning."""
    global next_move
    if depth == 0:
        return turn_multiplier * score_board(game_state)  # Leaf node evaluation

    max_score = -checkmate_points
    for move in valid_moves:
        game_state.make_move(move)
        next_moves = game_state.get_valid_moves()
        score = -find_negamax_move_alphabeta(game_state, next_moves, depth - 1, -beta, -alpha, -turn_multiplier)
        game_state.undo_move()

        if score > max_score:
            max_score = score
            if depth == set_depth:
                next_move = move  # Only store the move at the max depth

        # Alpha-beta pruning
        alpha = max(alpha, max_score)
        if alpha >= beta:
            break  # Cut-off branch

    return max_score
