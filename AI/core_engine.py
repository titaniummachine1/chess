"""
Fixed chess engine implementation with improved tactical awareness.
"""
import chess
import random
import time
from collections import OrderedDict

# Piece values in centipawns
PIECE_VALUES = {
    chess.PAWN: 100,
    chess.KNIGHT: 320,
    chess.BISHOP: 330, 
    chess.ROOK: 500,
    chess.QUEEN: 900,
    chess.KING: 20000
}

# Simplified piece-square tables for opening/middlegame
PIECE_SQUARE_TABLES = {
    # Pawns strongly favor center control and advancement
    chess.PAWN: [
        0,   0,   0,   0,   0,   0,   0,   0,
        50,  50,  50,  50,  50,  50,  50,  50,
        10,  10,  20,  30,  30,  20,  10,  10,
         5,   5,  10,  35,  35,  10,   5,   5,
         0,   0,   20,  40,  40,  20,   0,   0,
         5,  -5, -10,   0,   0, -10,  -5,   5,
         5,  10,  10, -20, -20,  10, -20, -20,  # severe penalty for g/h pawns
         0,   0,   0,   0,   0,   0,   0,   0
    ],
    # Knights prefer central squares, avoid edges
    chess.KNIGHT: [
        -50, -40, -30, -30, -30, -30, -40, -50,
        -40, -20,   0,   0,   0,   0, -20, -40,
        -30,   0,  10,  15,  15,  10,   0, -30,
        -30,   5,  15,  20,  20,  15,   5, -30,
        -30,   0,  15,  20,  20,  15,   0, -30,
        -30,   5,  10,  15,  15,  10,   5, -30,
        -40, -20,   0,   5,   5,   0, -20, -40,
        -50, -40, -30, -30, -30, -30, -40, -50
    ],
    # Bishops want to develop and control diagonals
    chess.BISHOP: [
        -20, -10, -10, -10, -10, -10, -10, -20,
        -10,   0,   0,   0,   0,   0,   0, -10,
        -10,   0,  10,  10,  10,  10,   0, -10,
        -10,   5,   5,  10,  10,   5,   5, -10,
        -10,   0,   5,  10,  10,   5,   0, -10,
        -10,  10,  10,  10,  10,  10,  10, -10,
        -10,   5,   0,   0,   0,   0,   5, -10,
        -20, -10, -10, -10, -10, -10, -10, -20
    ],
    # Rooks prefer open files, 7th rank is strong
    chess.ROOK: [
          0,   0,   0,   0,   0,   0,   0,   0,
          5,  10,  10,  10,  10,  10,  10,   5,
         -5,   0,   0,   0,   0,   0,   0,  -5,
         -5,   0,   0,   0,   0,   0,   0,  -5,
         -5,   0,   0,   0,   0,   0,   0,  -5,
         -5,   0,   0,   0,   0,   0,   0,  -5,
         -5,   0,   0,   0,   0,   0,   0,  -5,
          0,   0,   0,   5,   5,   0,   0,   0
    ],
    # Queen combines rook and bishop mobility
    chess.QUEEN: [
        -20, -10, -10,  -5,  -5, -10, -10, -20,
        -10,   0,   0,   0,   0,   0,   0, -10,
        -10,   0,   5,   5,   5,   5,   0, -10,
         -5,   0,   5,   5,   5,   5,   0,  -5,
          0,   0,   5,   5,   5,   5,   0,  -5,
        -10,   5,   5,   5,   5,   5,   0, -10,
        -10,   0,   5,   0,   0,   0,   0, -10,
        -20, -10, -10,  -5,  -5, -10, -10, -20
    ],
    # King wants to castle and stay safe in opening/middlegame
    chess.KING: [
        -30, -40, -40, -50, -50, -40, -40, -30,
        -30, -40, -40, -50, -50, -40, -40, -30,
        -30, -40, -40, -50, -50, -40, -40, -30,
        -30, -40, -40, -50, -50, -40, -40, -30,
        -20, -30, -30, -40, -40, -30, -30, -20,
        -10, -20, -20, -20, -20, -20, -20, -10,
         20,  20,   0,   0,   0,   0,  20,  20,
         20,  30,  10,   0,   0,  10,  30,  20
    ]
}

# Create a flipped version of tables for black
FLIPPED_PIECE_SQUARE_TABLES = {}
for piece_type, table in PIECE_SQUARE_TABLES.items():
    FLIPPED_PIECE_SQUARE_TABLES[piece_type] = list(reversed(table))

# Simple opening book for common first moves (key: board FEN, value: recommended move in UCI format)
OPENING_BOOK = {
    "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq -": ["e2e4", "d2d4"],  # Common White first moves
    "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq -": ["e7e5", "c7c5", "e7e6"],  # After 1.e4
    "rnbqkbnr/pppppppp/8/8/3P4/8/PPP1PPPP/RNBQKBNR b KQkq -": ["d7d5", "g8f6", "e7e6"]   # After 1.d4
}

def get_piece_value(piece_type):
    """Get base material value for a piece type"""
    return PIECE_VALUES.get(piece_type, 0)

def get_piece_square_value(piece_type, square, color):
    """Get positional value for a piece on a specific square"""
    if color == chess.WHITE:
        return PIECE_SQUARE_TABLES.get(piece_type, [0] * 64)[square]
    else:  # BLACK
        return FLIPPED_PIECE_SQUARE_TABLES.get(piece_type, [0] * 64)[square]

def is_piece_hanging(board, square):
    """Check if a piece is hanging (can be captured without loss)"""
    if square is None:
        return False
        
    piece = board.piece_at(square)
    if not piece:
        return False
        
    piece_value = get_piece_value(piece.piece_type)
    defender_color = piece.color
    attacker_color = not defender_color
    
    # Find all attackers and defenders
    attackers = list(board.attackers(attacker_color, square))
    defenders = list(board.attackers(defender_color, square))
    
    if not attackers:
        return False  # Piece is not under attack
        
    # Find lowest-valued attacker
    min_attacker_value = min(get_piece_value(board.piece_at(sq).piece_type) for sq in attackers)
    
    # If no defenders or lowest attacker is less valuable than piece, it's hanging
    if not defenders or min_attacker_value < piece_value:
        return True
        
    # Perform a mini-exchange simulation to check if piece is effectively hanging
    # This simulates captures and recaptures on the square
    remaining_piece_value = piece_value
    
    # Sort attackers and defenders by value (lowest first)
    attackers = sorted(attackers, key=lambda sq: get_piece_value(board.piece_at(sq).piece_type))
    defenders = sorted(defenders, key=lambda sq: get_piece_value(board.piece_at(sq).piece_type))
    
    attacking = True
    while attackers or defenders:
        if attacking:
            if not attackers:
                break
            attacker_sq = attackers.pop(0)
            attacker_value = get_piece_value(board.piece_at(attacker_sq).piece_type)
            if attacker_value > remaining_piece_value:
                # Not worth capturing
                break
            remaining_piece_value = attacker_value
        else:
            if not defenders:
                return True  # No more defenders, piece is lost
            defender_sq = defenders.pop(0)
            defender_value = get_piece_value(board.piece_at(defender_sq).piece_type)
            if defender_value > remaining_piece_value:
                # Not worth defending
                return True
            remaining_piece_value = defender_value
        attacking = not attacking
    
    return False

def see_capture(board, move):
    """Static Exchange Evaluation for a capture move"""
    if not board.is_capture(move):
        return 0
        
    # Get the target square and the captured piece's value
    target = move.to_square
    captured_piece_value = get_piece_value(board.piece_at(target).piece_type)
    
    # Make the capture
    board.push(move)
    
    # If the target square is now under attack, the opponent can recapture
    if any(board.attackers(not board.turn, target)):
        # Find the least valuable attacker for the recapture
        attackers = list(board.attackers(not board.turn, target))
        attacker_values = [get_piece_value(board.piece_at(sq).piece_type) for sq in attackers]
        least_valuable_attacker = attacker_values[attacker_values.index(min(attacker_values))]
        
        # Recursively evaluate the recapture
        recapture_value = see_capture(board, chess.Move.null())  # Placeholder for recapture
        board.pop()
        
        # Return the value of captured piece minus the SEE value of the recapture
        return captured_piece_value - least_valuable_attacker - recapture_value
    else:
        # No recapture possible
        board.pop()
        return captured_piece_value

def evaluate_board(board):
    """
    Evaluate the board position from white's perspective with enhanced tactical awareness.
    """
    if board.is_checkmate():
        return -10000 if board.turn == chess.WHITE else 10000
    if board.is_stalemate() or board.is_insufficient_material():
        return 0
        
    # Material + piece-square table evaluation
    score = 0
    for square, piece in board.piece_map().items():
        piece_value = get_piece_value(piece.piece_type)
        position_value = get_piece_square_value(piece.piece_type, square, piece.color)
        
        # Add value if white piece, subtract if black piece
        value = piece_value + position_value
        if piece.color == chess.WHITE:
            score += value
        else:
            score -= value
    
    # Mobility bonus (count legal moves)
    current_turn = board.turn
    
    # Evaluate white mobility
    board.turn = chess.WHITE
    white_moves = len(list(board.legal_moves))
    
    # Evaluate black mobility
    board.turn = chess.BLACK
    black_moves = len(list(board.legal_moves))
    
    # Restore the original turn
    board.turn = current_turn
    
    score += (white_moves - black_moves) * 5  # 5 centipawns per extra move
    
    # Center control bonus
    center_squares = [chess.D4, chess.E4, chess.D5, chess.E5]
    for square in center_squares:
        piece = board.piece_at(square)
        if piece:
            # Bonus for controlling center with a piece
            if piece.color == chess.WHITE:
                score += 15
            else:
                score -= 15
    
    # Development in opening
    if len(board.move_stack) < 15:  # Early game
        # Bonus for having castling rights
        if board.has_kingside_castling_rights(chess.WHITE):
            score += 20
        if board.has_queenside_castling_rights(chess.WHITE):
            score += 20
        if board.has_kingside_castling_rights(chess.BLACK):
            score -= 20
        if board.has_queenside_castling_rights(chess.BLACK):
            score -= 20
        
        # Penalties for early side pawn moves
        if len(board.move_stack) <= 2:
            for move in board.move_stack:
                from_file = chess.square_file(move.from_square)
                from_piece = board.piece_type_at(move.to_square)
                # Harsh penalty for early g/h pawn moves
                if from_piece == chess.PAWN and from_file in (6, 7):  # g/h files
                    if board.piece_at(move.to_square) and board.piece_at(move.to_square).color == chess.WHITE:
                        score -= 200  # White made a bad move
                    else:
                        score += 200  # Black made a bad move
    
    # Add hanging piece penalties
    hanging_penalties = 0
    for square, piece in board.piece_map().items():
        if is_piece_hanging(board, square):
            penalty = get_piece_value(piece.piece_type) * 0.8  # 80% of piece value as penalty
            if piece.color == chess.WHITE:
                hanging_penalties -= penalty
            else:
                hanging_penalties += penalty
    
    score += hanging_penalties
    return score

class TranspositionTable:
    """Simple fixed-size transposition table using replacement scheme"""
    def __init__(self, size=1000000):
        self.size = size  # Number of entries to store
        self.table = {}   # Key: Zobrist hash, Value: (depth, value, flag, best_move)
    
    def store(self, key, depth, value, flag, best_move):
        """Store a position's evaluation in the table"""
        # If we've reached capacity, clear 10% of the oldest entries
        if len(self.table) >= self.size:
            # Get a subset of keys to remove (oldest 10%)
            keys_to_remove = list(self.table.keys())[:self.size // 10]
            for k in keys_to_remove:
                del self.table[k]
        
        self.table[key] = (depth, value, flag, best_move)
    
    def lookup(self, key):
        """Look up a position in the table"""
        return self.table.get(key, None)

class ChessEngine:
    """Chess engine with alpha-beta search and basic move ordering"""
    
    def __init__(self):
        self.transposition_table = TranspositionTable()
        self.nodes_searched = 0
        self.start_time = 0
        self.time_limit = 5  # 5 seconds default time limit
    
    def is_time_up(self):
        """Check if search time is up"""
        return time.time() - self.start_time > self.time_limit
    
    def alpha_beta(self, board, depth, alpha, beta, maximizing):
        """
        Alpha-beta pruning search
        Returns (score, best_move)
        """
        # Check for timeout
        if self.is_time_up():
            return 0, None
            
        # Check transposition table
        key = str(board.fen())  # Simple hash for this implementation
        tt_entry = self.transposition_table.lookup(key)
        
        if tt_entry and tt_entry[0] >= depth:
            stored_depth, value, flag, move = tt_entry
            if flag == 'exact':
                return value, move
            elif flag == 'lower' and value >= beta:
                return value, move
            elif flag == 'upper' and value <= alpha:
                return value, move
        
        self.nodes_searched += 1
        
        # Check for terminal states
        if depth == 0:
            return self.quiescence_search(board, alpha, beta), None
        
        # Check opening book for very early positions
        if len(board.move_stack) < 3:
            fen_key = board.fen().split(' ')[0] + " " + ('w' if board.turn else 'b') + " " + board.fen().split(' ')[2]
            if fen_key in OPENING_BOOK:
                book_moves = OPENING_BOOK[fen_key]
                for move_uci in book_moves:
                    try:
                        move = chess.Move.from_uci(move_uci)
                        if move in board.legal_moves:
                            return 50, move  # Small bonus for book moves
                    except ValueError:
                        continue
        
        legal_moves = list(board.legal_moves)
        if not legal_moves:
            # Checkmate or stalemate
            if board.is_checkmate():
                return -9900 if maximizing else 9900, None
            return 0, None  # Draw
        
        # Order moves for better pruning
        ordered_moves = self.order_moves(board, legal_moves)
        
        best_move = None
        if maximizing:
            max_eval = float('-inf')
            for move in ordered_moves:
                # Always use a copy for board operations
                board_copy = board.copy()
                board_copy.push(move)
                eval_score, _ = self.alpha_beta(board_copy, depth-1, alpha, beta, False)
                
                if eval_score > max_eval:
                    max_eval = eval_score
                    best_move = move
                
                alpha = max(alpha, eval_score)
                if beta <= alpha or self.is_time_up():
                    break
            
            # Store the position in the transposition table
            flag = 'exact'
            if max_eval <= alpha:
                flag = 'upper'
            elif max_eval >= beta:
                flag = 'lower'
            self.transposition_table.store(key, depth, max_eval, flag, best_move)
            
            return max_eval, best_move
        else:
            min_eval = float('inf')
            for move in ordered_moves:
                # Always use a copy for board operations
                board_copy = board.copy()
                board_copy.push(move)
                eval_score, _ = self.alpha_beta(board_copy, depth-1, alpha, beta, True)
                
                if eval_score < min_eval:
                    min_eval = eval_score
                    best_move = move
                
                beta = min(beta, eval_score)
                if beta <= alpha or self.is_time_up():
                    break
            
            # Store the position in the transposition table
            flag = 'exact'
            if min_eval <= alpha:
                flag = 'upper'
            elif min_eval >= beta:
                flag = 'lower'
            self.transposition_table.store(key, depth, min_eval, flag, best_move)
            
            return min_eval, best_move
    
    def quiescence_search(self, board, alpha, beta, depth=0, max_depth=5):
        """
        Enhanced quiescence search that looks deeper into capture sequences
        and checks for hanging pieces to avoid tactical blunders.
        """
        # Check for timeout
        if self.is_time_up():
            return 0
            
        stand_pat = evaluate_board(board)
        if board.turn == chess.BLACK:
            stand_pat = -stand_pat
            
        if stand_pat >= beta:
            return beta
        if alpha < stand_pat:
            alpha = stand_pat
            
        # Stop if we've reached maximum quiescence depth
        if depth >= max_depth:
            return alpha
            
        # Generate and prioritize capture moves
        captures = []
        checks = []
        
        for move in board.legal_moves:
            if board.is_capture(move):
                victim = board.piece_at(move.to_square)
                attacker = board.piece_at(move.from_square)
                if victim and attacker:
                    # Prioritize MVV-LVA (Most Valuable Victim - Least Valuable Attacker)
                    score = 10 * get_piece_value(victim.piece_type) - get_piece_value(attacker.piece_type)
                    captures.append((score, move))
            elif board.gives_check(move):
                checks.append(move)
                
        # Sort captures by MVV-LVA score
        captures.sort(reverse=True)
        captures = [move for _, move in captures]
        
        # Search captures first
        for move in captures:
            board_copy = board.copy()
            board_copy.push(move)
            score = -self.quiescence_search(board_copy, -beta, -alpha, depth + 1, max_depth)
            
            if score >= beta:
                return beta
            if score > alpha:
                alpha = score
                
        # Then search checks if we're not too deep
        if depth < 2:  # Limit check searching to avoid explosion
            for move in checks:
                board_copy = board.copy()
                board_copy.push(move)
                score = -self.quiescence_search(board_copy, -beta, -alpha, depth + 1, max_depth)
                
                if score >= beta:
                    return beta
                if score > alpha:
                    alpha = score
        
        return alpha
    
    def order_moves(self, board, moves):
        """Order moves for better pruning with enhanced tactical awareness"""
        move_scores = []
        
        # Check which pieces are hanging (can be captured for free)
        hanging_squares = []
        for square, piece in board.piece_map().items():
            if piece.color == board.turn and is_piece_hanging(board, square):
                hanging_squares.append(square)
        
        for move in moves:
            score = 0
            
            # Prioritize moves that save hanging pieces
            if move.from_square in hanging_squares:
                score += 1000
            
            # Captures scored by SEE
            if board.is_capture(move):
                victim = board.piece_at(move.to_square)
                attacker = board.piece_at(move.from_square)
                if victim and attacker:
                    # MVP-LVA + rough SEE estimate
                    trade_value = get_piece_value(victim.piece_type) - get_piece_value(attacker.piece_type)/10
                    
                    # Check if the capture leads to piece loss
                    board_copy = board.copy()
                    board_copy.push(move)
                    if is_piece_hanging(board_copy, move.to_square):
                        trade_value -= get_piece_value(attacker.piece_type)
                        
                    score += max(0, trade_value) * 10
            
            # Promotion bonus
            if move.promotion:
                score += get_piece_value(move.promotion)
            
            # Check bonus
            board_copy = board.copy()  # Use a copy
            board_copy.push(move)
            if board_copy.is_check():
                score += 50
            
            # Central pawn moves in opening
            if board.piece_at(move.from_square) and board.piece_at(move.from_square).piece_type == chess.PAWN:
                if len(board.move_stack) < 10:  # Opening phase
                    # Central pawn moves
                    if (move.to_square in [chess.D4, chess.E4, chess.D5, chess.E5] or 
                        move.to_square in [chess.D3, chess.E3, chess.D6, chess.E6]):
                        score += 30
                        
                    # Penalty for early g/h pawn moves
                    from_file = chess.square_file(move.from_square)
                    if from_file in (6, 7) and len(board.move_stack) <= 4:  # g/h files in early game
                        score -= 100  # Strong penalty
            
            # Development bonus in opening
            if len(board.move_stack) < 10:
                if board.piece_at(move.from_square) and board.piece_at(move.from_square).piece_type in [chess.KNIGHT, chess.BISHOP]:
                    if (move.from_square in [chess.B1, chess.G1, chess.C1, chess.F1] and board.turn == chess.WHITE) or \
                       (move.from_square in [chess.B8, chess.G8, chess.C8, chess.F8] and board.turn == chess.BLACK):
                        score += 25
            
            # Castling is very good in opening
            if board.is_castling(move):
                score += 60
            
            move_scores.append((move, score))
        
        move_scores.sort(key=lambda x: x[1], reverse=True)
        return [move for move, _ in move_scores]
    
    def search(self, board, depth=3, time_limit=5):
        """
        Public search method that runs iterative deepening
        """
        # Always work with a copy of the board
        board = board.copy()
        
        self.nodes_searched = 0
        self.start_time = time.time()
        self.time_limit = time_limit
        
        best_move = None
        best_score = 0
        
        # Check opening book first
        fen_key = board.fen().split(' ')[0] + " " + ('w' if board.turn else 'b') + " " + board.fen().split(' ')[2]
        if fen_key in OPENING_BOOK:
            book_moves = OPENING_BOOK[fen_key]
            for move_uci in book_moves:
                try:
                    move = chess.Move.from_uci(move_uci)
                    if move in board.legal_moves:
                        print(f"Using book move: {move}")
                        return move
                except ValueError:
                    continue
        
        for current_depth in range(1, depth + 1):
            if self.is_time_up():
                break
                
            print(f"Searching at depth {current_depth}...")
            
            # Set the side to move correctly
            maximizing = board.turn == chess.WHITE
            
            # Run alpha-beta search
            score, current_best_move = self.alpha_beta(
                board, 
                current_depth, 
                float('-inf'), 
                float('inf'), 
                maximizing
            )
            
            if current_best_move:
                best_move = current_best_move
                best_score = score
                
            sign = 1 if board.turn == chess.WHITE else -1
            print(f"Depth: {current_depth}, Score: {sign * score}, Best move: {best_move}")
            
            if self.is_time_up():
                print("Search time limit reached")
                break
        
        print(f"Nodes searched: {self.nodes_searched}")
        print(f"Time taken: {time.time() - self.start_time:.2f} seconds")
        
        # If no legal moves or other error, pick a random legal move as fallback
        if not best_move:
            try:
                legal_moves = list(board.legal_moves)
                
                # Filter out obviously bad moves in the opening
                if len(board.move_stack) <= 2:
                    safe_moves = []
                    for move in legal_moves:
                        from_piece = board.piece_at(move.from_square)
                        if from_piece and from_piece.piece_type == chess.PAWN:
                            from_file = chess.square_file(move.from_square)
                            # Avoid early g/h pawn moves
                            if from_file not in (6, 7):  # Not g/h files
                                safe_moves.append(move)
                        else:
                            safe_moves.append(move)
                    
                    if safe_moves:
                        best_move = random.choice(safe_moves)
                    else:
                        best_move = random.choice(legal_moves)
                else:
                    best_move = random.choice(legal_moves)
                    
                print("Selecting random move as fallback")
            except IndexError:
                print("No legal moves available")
        
        # When returning move, make one final safety check
        if best_move:
            # Check if move hangs a major piece (queen or rook)
            test_board = board.copy()
            test_board.push(best_move)
            
            for sq, piece in test_board.piece_map().items():
                if (piece.color == board.turn and piece.piece_type in [chess.QUEEN, chess.ROOK] and 
                    is_piece_hanging(test_board, sq)):
                    print(f"Safety check detected hanging {piece.symbol()} after {best_move}, selecting alternative")
                    
                    # Try to find non-blundering move
                    for move in ordered_moves:
                        if move != best_move:
                            alt_board = board.copy()
                            alt_board.push(move)
                            safe = True
                            
                            for alt_sq, alt_piece in alt_board.piece_map().items():
                                if (alt_piece.color == board.turn and 
                                    alt_piece.piece_type in [chess.QUEEN, chess.ROOK] and 
                                    is_piece_hanging(alt_board, alt_sq)):
                                    safe = False
                                    break
                                    
                            if safe:
                                print(f"Selected safer alternative: {move}")
                                return move
                    
                    # If all moves hang something, pick the least valuable piece to hang
                    least_value = float('inf')
                    safest_move = None
                    
                    for move in ordered_moves:
                        alt_board = board.copy()
                        alt_board.push(move)
                        max_loss = 0
                        
                        for alt_sq, alt_piece in alt_board.piece_map().items():
                            if (alt_piece.color == board.turn and 
                                is_piece_hanging(alt_board, alt_sq)):
                                max_loss = max(max_loss, get_piece_value(alt_piece.piece_type))
                                
                        if max_loss < least_value:
                            least_value = max_loss
                            safest_move = move
                    
                    if safest_move:
                        print(f"No completely safe moves. Selected: {safest_move}")
                        return safest_move
        
        return best_move

# Function to use for the main AI interface
def best_move(board, depth):
    # Make sure we work with a copy of the board
    board_copy = board.copy()
    engine = ChessEngine()
    return engine.search(board_copy, depth=depth, time_limit=5)  # 5 second time limit
