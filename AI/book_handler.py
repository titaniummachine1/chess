"""
Advanced book move handling with statistical analysis and smart interpolation
"""
import chess
import random
import math
import numpy as np
from AI.book_parser import OPENING_BOOK

class BookMoveSelector:
    """
    Handles advanced book move selection with statistical weighting
    and piece-square table adjustments.
    """
    def __init__(self):
        self.recent_positions = {}
        self.position_weights = {}
        self.main_book_moves = []
        
    def get_weighted_book_move(self, board):
        """
        Get book moves with statistical weighting.
        Returns both a suggested move and additional info including:
        - book_move_bonuses: Dict with bonus values for each book move
        - special_move: The randomly selected move with extra bonus (if any)
        """
        # Get all book moves for current position
        book_moves = OPENING_BOOK.get_book_moves(board)
        
        if not book_moves:
            return None, {"book_move_bonuses": {}, "special_move": None}
            
        # Force new randomization each time - make sure to seed differently
        import time
        random.seed(time.time() + hash(board.fen()) % 1000)
        
        # Check for drawbacks which might affect move selection
        active_drawback = None
        if hasattr(board, 'get_active_drawback'):
            active_drawback = board.get_active_drawback(board.turn)
            
        # Filter legal moves considering drawbacks
        legal_book_moves = []
        for move, freq in book_moves:
            if move in board.legal_moves:
                legal_book_moves.append((move, freq))
            
        if not legal_book_moves:
            return None, {"book_move_bonuses": {}, "special_move": None}
        
        # Sort moves by frequency/weight in descending order to prioritize stronger moves
        sorted_moves = sorted(legal_book_moves, key=lambda x: x[1], reverse=True)
        
        # Select the best move (highest frequency) as the primary choice
        best_move = sorted_moves[0][0]
        
        # Create book move bonuses dictionary - give small bonuses proportional to move frequency
        book_move_bonuses = {}
        total_freq = sum(freq for _, freq in sorted_moves)
        
        for move, freq in sorted_moves:
            # Calculate bonus as percentage of move frequency compared to total
            # Higher frequency moves get larger bonuses, capped at 30 centipawns
            if total_freq > 0:
                bonus = min(30, int(30 * freq / total_freq))
            else:
                bonus = 5  # Default small bonus
            
            book_move_bonuses[move] = bonus
        
        # Provide a modest bonus (20cp) to the best move
        special_move = best_move
        book_move_bonuses[special_move] = max(20, book_move_bonuses.get(special_move, 0))
        
        # Return the best move and additional info
        return best_move, {
            "book_move_bonuses": book_move_bonuses,
            "special_move": special_move,
            "all_book_moves": [move for move, _ in sorted_moves]
        }
        
    def adjust_piece_square_values(self, board, color, move, pst_values, weights):
        """
        Adjust piece-square values based on book move bell curve weights
        
        Args:
            board: The current board position
            color: The color to adjust values for
            move: A chess.Move object to analyze
            pst_values: The original PST values (dict mapping squares to values)
            weights: Dict with "weights" mapping book moves to bell curve values,
                    and "default" for non-book moves
        """
        if not weights or "weights" not in weights:
            return pst_values.copy()
            
        result = {}
        book_weights = weights["weights"]
        default_weight = weights.get("default", 0.3)
        
        # For each square on the board
        for square in chess.SQUARES:
            # Get original PST value
            orig_value = pst_values.get(square, 0)
            
            # Only adjust positive values from our perspective
            if (color == chess.WHITE and orig_value > 0) or (color == chess.BLACK and orig_value < 0):
                # Check if this square is involved in any book moves
                square_weight = default_weight
                
                # Check if this square is a target of any main book move
                for book_move, weight in book_weights.items():
                    if book_move.to_square == square:
                        square_weight = max(square_weight, weight)
                        break
                
                # Adjust the PST value
                if color == chess.WHITE:
                    # For white, increase positive values
                    result[square] = orig_value * (0.5 + 0.5 * square_weight)
                else:
                    # For black, make negative values more negative
                    result[square] = orig_value * (0.5 + 0.5 * square_weight)
            else:
                # Keep original value for non-positive values
                
                result[square] = orig_value
                
        return result

# Singleton instance for reuse
BOOK_SELECTOR = BookMoveSelector()
