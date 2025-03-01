import numpy as np
import chess
from GameState.movegen import DrawbackBoard
import random
from collections import namedtuple

# For backward compatibility
from AI.evaluation import Evaluator, Score

# Set to True to see verbose debug output including principal variation
DEBUG = False

###############################################################################
# Zobrist Hashing
###############################################################################

class ZobristHasher:
    """Class for managing Zobrist hashing for transposition tables."""
    
    def __init__(self):
        # Initialize tables with None values to be filled on first use
        self.piece_table = {}
        self.castling_table = {right: random.getrandbits(64) for right in "KQkq"}
        self.ep_table = [random.getrandbits(64) for _ in range(64)]
        self.turn_white = 0xF0F0F0F0F0F0F0F0
        self.turn_black = 0x0F0F0F0F0F0F0F0F
    
    def compute_hash(self, board):
        """Compute the Zobrist hash for a given board position."""
        key = 0
        
        # Add piece contributions
        for square, piece in board.piece_map().items():
            symbol = piece.symbol() if hasattr(piece, "symbol") else str(piece)
            hash_key = (square, symbol)
            
            # Create hash values for new positions on demand
            if hash_key not in self.piece_table:
                self.piece_table[hash_key] = random.getrandbits(64)
                
            key ^= self.piece_table[hash_key]
        
        # Add turn contribution
        key ^= self.turn_white if board.turn == chess.WHITE else self.turn_black
        
        # Add castling rights contribution
        castling = board.castling_xfen() if hasattr(board, "castling_xfen") else board.castling_xfen()
        for char in castling:
            if char in self.castling_table:
                key ^= self.castling_table[char]
        
        # Add en passant contribution
        if board.ep_square is not None:
            key ^= self.ep_table[board.ep_square]
            
        return key
    
    def get_hash(self, board):
        """Get the hash for a board, using cached value if available."""
        if hasattr(board, "zobrist_key"):
            return board.zobrist_key
        return self.compute_hash(board)

###############################################################################
# Move Scoring
###############################################################################

class MoveScorer:
    """Class for scoring moves for move ordering."""
    
    def __init__(self, evaluator):
        self.evaluator = evaluator
    
    def score_move(self, board, move):
        """
        Score a move for move ordering. Higher scores are searched first.
        Uses MVV-LVA for captures and piece-square improvements for non-captures.
        """
        score = 0
        
        # Check if this is a capture
        captured_piece = board.piece_at(move.to_square)
        attacker = board.piece_at(move.from_square)
        
        if captured_piece:
            if captured_piece.piece_type == chess.KING:
                return 1000000  # King capture gets highest priority
                
            # Most Valuable Victim - Least Valuable Attacker (MVV-LVA)
            victim_value = self.evaluator.get_piece_value(board, captured_piece.piece_type, captured_piece.color)
            attacker_value = self.evaluator.get_piece_value(board, attacker.piece_type, attacker.color)
            score = victim_value * 10 - attacker_value
        
        # Add bonus for targeting the opponent's last moved piece
        if self._targets_last_moved_piece(board, move):
            score += 300
        
        # If not a capture or the score is still 0, add piece-square table improvement
        if score == 0 and hasattr(board, "piece_square_tables"):
            piece = board.piece_at(move.from_square)
            if piece:
                # Calculate the improvement in piece position
                score = self._calculate_position_improvement(board, move, piece)
        
        return score
    
    def _targets_last_moved_piece(self, board, move):
        """Check if this move targets the last moved piece."""
        if not hasattr(board, 'move_stack') or not board.move_stack:
            return False
            
        last_move = board.move_stack[-1]
        last_move_to_square = last_move.to_square
        
        # Direct capture of last moved piece
        if move.to_square == last_move_to_square:
            return True
            
        # Checking if the move attacks the square of the last moved piece
        piece = board.piece_at(move.from_square)
        if not piece:
            return False
            
        # Simple attack detection based on piece type
        file_diff = abs(chess.square_file(move.to_square) - chess.square_file(last_move_to_square))
        rank_diff = abs(chess.square_rank(move.to_square) - chess.square_rank(last_move_to_square))
        
        if piece.piece_type == chess.PAWN:
            if piece.color == chess.WHITE:
                return last_move_to_square in [move.to_square + 7, move.to_square + 9]
            else:
                return last_move_to_square in [move.to_square - 7, move.to_square - 9]
        
        elif piece.piece_type == chess.KNIGHT:
            return (file_diff == 1 and rank_diff == 2) or (file_diff == 2 and rank_diff == 1)
        
        elif piece.piece_type == chess.BISHOP:
            return file_diff == rank_diff
        
        elif piece.piece_type == chess.ROOK:
            return file_diff == 0 or rank_diff == 0
        
        elif piece.piece_type == chess.QUEEN:
            return file_diff == rank_diff or file_diff == 0 or rank_diff == 0
            
        return False
    
    def _calculate_position_improvement(self, board, move, piece):
        """Calculate the improvement in position based on piece-square tables."""
        if not hasattr(board, "piece_square_tables"):
            return 0
            
        pst = board.piece_square_tables
        phase = pst.compute_game_phase(board)
        piece_symbol = piece.symbol().upper()
        
        # Calculate position improvement
        if piece.color == chess.WHITE:
            from_mg = pst.piece_square_tables["mg"].get(piece_symbol, [0]*64)[move.from_square]
            from_eg = pst.piece_square_tables["eg"].get(piece_symbol, [0]*64)[move.from_square]
            to_mg = pst.piece_square_tables["mg"].get(piece_symbol, [0]*64)[move.to_square]
            to_eg = pst.piece_square_tables["eg"].get(piece_symbol, [0]*64)[move.to_square]
        else:
            from_mg = pst.flipped_piece_square_tables["mg"].get(piece_symbol, [0]*64)[move.from_square]
            from_eg = pst.flipped_piece_square_tables["eg"].get(piece_symbol, [0]*64)[move.from_square]
            to_mg = pst.flipped_piece_square_tables["mg"].get(piece_symbol, [0]*64)[move.to_square]
            to_eg = pst.flipped_piece_square_tables["eg"].get(piece_symbol, [0]*64)[move.to_square]
        
        # Interpolate between midgame and endgame values
        from_value = from_mg * phase + from_eg * (1 - phase)
        to_value = to_mg * phase + to_eg * (1 - phase)
        
        # Score based on improvement
        return to_value - from_value

###############################################################################
# Search Enhancements & Searcher Class
###############################################################################

# Transposition table entry: (lower bound, upper bound)
Entry = namedtuple("Entry", "lower upper")

class Searcher:
    """Chess engine search class with alpha-beta pruning and various enhancements."""
    
    def __init__(self, evaluator=None, piece_square_tables=None):
        """
        Initialize the searcher with optional evaluator and piece-square tables.
        
        Args:
            evaluator: An Evaluator instance for board evaluation
            piece_square_tables: A module providing piece-square table functionality
        """
        # Create default evaluator if none provided
        self.evaluator = evaluator if evaluator else Evaluator(piece_square_tables)
        self.piece_square_tables = piece_square_tables
        
        # Create other helper components
        self.zobrist_hasher = ZobristHasher()
        self.move_scorer = MoveScorer(self.evaluator)
        
        # Initialize search state
        self.tp_score = {}   # key: (zobrist key + ":" + depth)
        self.tp_move = {}    # key: zobrist key -> best move found
        self.nodes = 0
        self.killer_moves = {}    # key: depth -> list of moves causing beta cutoffs
        self.history_table = {}   # key: move -> heuristic score
        self.search_board = None  # Internal board copy for search operations
    
    def move_ordering_score(self, board, move, depth):
        """Score moves for search ordering, including killer and history heuristics."""
        base = self.move_scorer.score_move(board, move)
        killer_bonus = 5000 if move in self.killer_moves.get(depth, []) else 0
        history_bonus = self.history_table.get(str(move), 0)
        return base + killer_bonus + history_bonus
    
    def quiescence(self, board, alpha, beta):
        """
        Quiescence search to resolve tactical sequences.
        Evaluates only capture moves to find a "quiet" position.
        """
        self.nodes += 1
        
        # Check for terminal positions
        result = self._is_game_over(board)
        if result is not None:
            return result
        
        # Stand pat evaluation
        stand_pat = self.evaluator.evaluate_board(board)
        
        if stand_pat >= beta:
            return beta
        if alpha < stand_pat:
            alpha = stand_pat
        
        # Consider only captures and checks
        moves = [m for m in board.generate_legal_moves()
                 if self._is_capture(board, m) or 
                 (hasattr(board, "gives_check") and board.gives_check(m))]
                 
        # Order moves to improve pruning
        moves.sort(key=lambda m: self.move_scorer.score_move(board, m), reverse=True)
        
        for move in moves:
            board.push(move)
            score = -self.quiescence(board, -beta, -alpha)
            board.pop()
            
            if score >= beta:
                return beta
            if score > alpha:
                alpha = score
                
        return alpha
    
    def bound(self, board, gamma, depth):
        """
        Alpha-beta search with null-window (Principal Variation Search).
        Uses transposition table and various search enhancements.
        
        Args:
            board: Chess board to search
            gamma: The null-window bound
            depth: Remaining search depth
            
        Returns:
            Best score found at this position
        """
        self.nodes += 1
        
        # Check for terminal positions
        result = self._is_game_over(board)
        if result is not None:
            return result
            
        # Leaf node - use quiescence search for stable evaluation
        if depth == 0:
            return self.quiescence(board, -Score.CHECKMATE.value, Score.CHECKMATE.value)
        
        # Check transposition table
        key = f"{self.zobrist_hasher.get_hash(board)}:{depth}"
        entry = self.tp_score.get(key, Entry(-Score.CHECKMATE.value, Score.CHECKMATE.value))
        
        # If position is already solved, return cached value
        if entry.lower >= gamma:
            return entry.lower
        if entry.upper < gamma:
            return entry.upper
        
        # Null-move pruning - skip our turn if not in check and at sufficient depth
        if depth >= 3 and hasattr(board, "push_null") and not board.is_check():
            board.push_null()
            null_score = -self.bound(board, 1 - gamma, depth - 2)
            board.pop_null()
            if null_score >= gamma:
                return null_score
        
        # Generate and sort legal moves
        moves = list(board.generate_legal_moves())
        
        # Handle special cases
        if not moves:
            return -Score.CHECKMATE.value // 2  # No moves is bad but not an immediate loss
            
        # Check for immediate king capture
        if self._has_immediate_king_capture(board, moves):
            return Score.CHECKMATE.value
        
        # Order moves using combined heuristics
        moves.sort(key=lambda m: self.move_ordering_score(board, m, depth), reverse=True)
        
        best = -Score.CHECKMATE.value
        for i, move in enumerate(moves):
            # Late Move Reductions (LMR) - reduce search depth for likely poor moves
            reduction = 1 if i >= 2 and depth >= 3 and not self._is_capture(board, move) else 0
            
            # Search extensions for tactically important positions
            extension = self._calculate_extension(board, move)
            
            # Make the move and search recursively
            board.push(move)
            score = -self.bound(board, 1 - gamma, depth - 1 - reduction + extension)
            board.pop()
            
            if score > best:
                best = score
                
            if best >= gamma:
                # Update killer moves and history heuristics
                self.killer_moves.setdefault(depth, []).append(move)
                self.history_table[str(move)] = self.history_table.get(str(move), 0) + depth * depth
                self.tp_move[self.zobrist_hasher.get_hash(board)] = move
                break
        
        # Update transposition table
        if best >= gamma:
            self.tp_score[key] = Entry(best, entry.upper)
        else:
            self.tp_score[key] = Entry(entry.lower, best)
            
        return best
    
    def get_principal_variation(self, board, max_length=10):
        """
        Extract the principal variation (best line of play) from the transposition table.
        
        Args:
            board: Starting board position
            max_length: Maximum number of moves to include
            
        Returns:
            List of moves representing the best line
        """
        pv = []
        local_board = board.copy()
        
        while True:
            key = self.zobrist_hasher.get_hash(local_board)
            if key not in self.tp_move:
                break
                
            move = self