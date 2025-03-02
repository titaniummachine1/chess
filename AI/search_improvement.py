import chess
import numpy as np
from collections import defaultdict

# Static Exchange Evaluation (SEE) tables for better move evaluation
PIECE_VALUES = {
    chess.PAWN: 100,
    chess.KNIGHT: 280,
    chess.BISHOP: 320,
    chess.ROOK: 479,
    chess.QUEEN: 929,
    chess.KING: 20000
}

class ImprovedMoveOrdering:
    """
    Advanced move ordering system based on Numbfish techniques.
    - Better capture evaluation using SEE (Static Exchange Evaluation)
    - History heuristic for quiet moves
    - Killer move tracking
    - PV move prioritization
    """
    def __init__(self):
        # History table stores success of quiet moves
        self.history_table = defaultdict(int)
        # Killer move table stores good non-capture moves at each depth
        self.killer_moves = {}
        # Counter for move ordering statistics
        self.cutoff_counts = [0, 0, 0, 0]  # PV, Capture, Killer, History
    
    def reset_statistics(self):
        self.cutoff_counts = [0, 0, 0, 0]
    
    def score_move(self, board, move, pv_move=None, depth=0):
        """
        Score a move for ordering in the search:
        1. PV moves (highest priority)
        2. Good captures based on MVV-LVA
        3. Killer moves
        4. History heuristic moves
        5. Bad captures
        6. Other quiet moves
        """
        # PV move gets highest score
        if pv_move and move == pv_move:
            return 20000
        
        # Check if capture
        if board.is_capture(move):
            # Most Valuable Victim - Least Valuable Attacker
            victim_value = PIECE_VALUES.get(board.piece_at(move.to_square).piece_type, 0)
            aggressor_value = PIECE_VALUES.get(board.piece_at(move.from_square).piece_type, 0)
            
            # SEE estimation - prioritize captures that gain material
            if victim_value >= aggressor_value:
                return 10000 + victim_value - aggressor_value//100
            else:
                # Bad captures go below killers but above regular moves
                return 5000 + victim_value - aggressor_value//100
        
        # Check if killer move
        if depth in self.killer_moves and move in self.killer_moves[depth]:
            return 9000 - self.killer_moves[depth].index(move)
        
        # History heuristic (normalized to avoid overflow)
        history_score = min(self.history_table[(board.turn, move.from_square, move.to_square)], 2000)
        
        # Check special moves
        if board.is_castling(move):
            return 8500  # Castling is usually good
        
        # Add bonus for moves to the center and penalties for edge moves
        center_bonus = 0
        to_file = chess.square_file(move.to_square)
        to_rank = chess.square_rank(move.to_square)
        if to_file in (3, 4) and to_rank in (3, 4):
            center_bonus = 50
        elif to_file in (0, 7) or to_rank in (0, 7):
            center_bonus = -30
            
        # Return weighted score for quiet moves
        return 5000 + history_score + center_bonus
    
    def add_killer_move(self, move, depth):
        """Add a move to killer moves table"""
        if depth not in self.killer_moves:
            self.killer_moves[depth] = []
            
        # Don't add the same move twice
        if move in self.killer_moves[depth]:
            return
            
        # Add at the beginning, maintain a list of max 2 killers
        self.killer_moves[depth].insert(0, move)
        if len(self.killer_moves[depth]) > 2:
            self.killer_moves[depth].pop()
    
    def update_history(self, board, move, depth):
        """Update history table based on move's success"""
        # Increase history score for successful moves proportional to depth
        piece = board.piece_at(move.from_square)
        if piece and not board.is_capture(move):
            key = (board.turn, move.from_square, move.to_square)
            # Square the depth to give preference to deeper cutoffs
            self.history_table[key] += depth * depth
            
            # Age all history values periodically to avoid overflow
            if max(self.history_table.values()) > 1000000:
                for k in self.history_table:
                    self.history_table[k] = self.history_table[k] // 2
    
    def sort_moves(self, board, moves, pv_move=None, depth=0):
        """Sort moves according to the scoring function"""
        # Score moves
        scored_moves = [(self.score_move(board, move, pv_move, depth), move) for move in moves]
        # Sort by score in descending order
        scored_moves.sort(reverse=True)
        # Return just the moves
        return [move for _, move in scored_moves]
