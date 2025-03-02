"""
Simple, robust chess engine implementation focused on core functionality.
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
         5,   5,  10,  25,  25,  10,   5,   5,
         0,   0,   0,  20,  20,   0,   0,   0,
         5,  -5, -10,   0,   0, -10,  -5,   5,
         5,  10,  10, -20, -20,  10,  10,   5,
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

def get_piece_value(piece_type):
    """Get base material value for a piece type"""
    return PIECE_VALUES.get(piece_type, 0)

def get_piece_square_value(piece_type, square, color):
    """Get positional value for a piece on a specific square"""
    if color == chess.WHITE:
        return PIECE_SQUARE_TABLES.get(piece_type, [0] * 64)[square]
    else:  # BLACK
        return FLIPPED_PIECE_SQUARE_TABLES.get(piece_type, [0] * 64)[square]

def evaluate_board(board):
    """
    Evaluate the board position from white's perspective.
    Returns a positive score if white is better, negative if black is better.
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
                score += 10
            else:
                score -= 10
    
    # Development in opening
    if len(board.move_stack) < 15:  # Early game
        if board.has_kingside_castling_rights(chess.WHITE):
            score += 15  # Bonus for having castling rights
        if board.has_queenside_castling_rights(chess.WHITE):
            score += 15
        if board.has_kingside_castling_rights(chess.BLACK):
            score -= 15
        if board.has_queenside_castling_rights(chess.BLACK):
            score -= 15
    
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
    
    def alpha_beta(self, board, depth, alpha, beta, maximizing):
        """
        Alpha-beta pruning search
        Returns (score, best_move)
        """
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
                board.push(move)
                eval_score, _ = self.alpha_beta(board, depth-1, alpha, beta, False)
                board.pop()
                
                if eval_score > max_eval:
                    max_eval = eval_score
                    best_move = move
                
                alpha = max(alpha, eval_score)
                if beta <= alpha:
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
                board.push(move)
                eval_score, _ = self.alpha_beta(board, depth-1, alpha, beta, True)
                board.pop()
                
                if eval_score < min_eval:
                    min_eval = eval_score
                    best_move = move
                
                beta = min(beta, eval_score)
                if beta <= alpha:
                    break
            
            # Store the position in the transposition table
            flag = 'exact'
            if min_eval <= alpha:
                flag = 'upper'
            elif min_eval >= beta:
                flag = 'lower'
            self.transposition_table.store(key, depth, min_eval, flag, best_move)
            
            return min_eval, best_move
    
    def quiescence_search(self, board, alpha, beta):
        """
        Search captures until a quiet position is reached
        to address the horizon effect
        """
        stand_pat = evaluate_board(board) if board.turn == chess.WHITE else -evaluate_board(board)
        
        if stand_pat >= beta:
            return beta
        if alpha < stand_pat:
            alpha = stand_pat
        
        # Only consider captures
        captures = [move for move in board.legal_moves if board.is_capture(move)]
        captures = self.order_moves(board, captures)
        
        for move in captures:
            board.push(move)
            score = -self.quiescence_search(board, -beta, -alpha)
            board.pop()
            
            if score >= beta:
                return beta
            if score > alpha:
                alpha = score
        
        return alpha
    
    def order_moves(self, board, moves):
        """Order moves for better pruning efficiency"""
        move_scores = []
        
        for move in moves:
            score = 0
            
            # Captures are scored by MVV-LVA (Most Valuable Victim - Least Valuable Aggressor)
            if board.is_capture(move):
                victim = board.piece_at(move.to_square)
                aggressor = board.piece_at(move.from_square)
                if victim and aggressor:  # Ensure pieces exist
                    score += 10 * get_piece_value(victim.piece_type) - get_piece_value(aggressor.piece_type)
            
            # Promotion bonus
            if move.promotion:
                score += get_piece_value(move.promotion)
            
            # Check bonus
            board.push(move)
            if board.is_check():
                score += 50
            board.pop()
            
            # Central pawn moves in opening
            if board.piece_at(move.from_square) and board.piece_at(move.from_square).piece_type == chess.PAWN:
                if len(board.move_stack) < 10:  # Opening phase
                    # Central pawn moves
                    if (move.to_square in [chess.D4, chess.E4, chess.D5, chess.E5] or 
                        move.to_square in [chess.D3, chess.E3, chess.D6, chess.E6]):
                        score += 30
            
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
        
        # Sort moves by score in descending order
        move_scores.sort(key=lambda x: x[1], reverse=True)
        return [move for move, _ in move_scores]
    
    def search(self, board, depth=3):
        """
        Public search method that runs iterative deepening
        """
        self.nodes_searched = 0
        start_time = time.time()
        
        # Adjust depth for the side to move
        actual_max_depth = depth
        
        best_move = None
        for current_depth in range(1, actual_max_depth + 1):
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
                
            sign = 1 if board.turn == chess.WHITE else -1
            print(f"Depth: {current_depth}, Score: {sign * score}, Best move: {best_move}")
            
            # Time check (optional safety feature)
            if time.time() - start_time > 10:  # 10 seconds max
                print("Search time limit reached")
                break
        
        print(f"Nodes searched: {self.nodes_searched}")
        print(f"Time taken: {time.time() - start_time:.2f} seconds")
        
        # If no legal moves or other error, pick a random legal move as fallback
        if not best_move:
            try:
                best_move = random.choice(list(board.legal_moves))
                print("Selecting random move as fallback")
            except IndexError:
                print("No legal moves available")
        
        return best_move

# Function to use for the main AI interface
def best_move(board, depth):
    engine = ChessEngine()
    return engine.search(board, depth)
