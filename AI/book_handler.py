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
        print(f"BOOK DEBUG: Found {len(book_moves)} book moves for current position")
        
        if not book_moves:
            return None, {"book_move_bonuses": {}, "special_move": None}
            
        # Print all available book moves with their weights
        print(f"BOOK DEBUG: Available moves: {', '.join([f'{move}:{weight}' for move, weight in book_moves])}")
        
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
            else:
                print(f"BOOK DEBUG: Move {move} is not legal with current drawback")
        
        # If no legal book moves remain after filtering
        if not legal_book_moves:
            return None, {"book_move_bonuses": {}, "special_move": None}
            
        book_moves = legal_book_moves
        
        # Calculate move weights based on frequency
        total_freq = sum(freq for _, freq in book_moves)
        if total_freq == 0:
            return None, {"book_move_bonuses": {}, "special_move": None}
            
        # Normalize frequencies to get probabilities
        move_probs = {}
        for move, freq in book_moves:
            # Add random variation (+/- 20%) to each probability for more diversity
            random_factor = 0.8 + 0.4 * random.random()  # 0.8 to 1.2
            
            # Reduce probability further if there's an active drawback
            if active_drawback:
                # More randomness with drawbacks to avoid predictable patterns
                drawback_factor = 0.6 + 0.8 * random.random()  # 0.6 to 1.4
                random_factor *= drawback_factor
                
            normalized_prob = ((freq + 1) / (total_freq + len(book_moves))) * random_factor
            move_probs[move] = normalized_prob
        
        # Select suggested move weighted by probability
        moves = list(move_probs.keys())
        probs = [move_probs[m] for m in moves]
        total_prob = sum(probs)
        if total_prob > 0:  # Normalize probabilities
            probs = [p/total_prob for p in probs]
        
        # Select a special move to get extra bonus
        special_move = None
        if moves:
            special_move = random.choices(moves, weights=probs, k=1)[0]
            print(f"BOOK DEBUG: Special move selected: {special_move} (gets 30cp bonus)")
            
        # Prepare bonus values for all book moves - standard 25cp (0.25 pawns)
        # Special move gets 30cp (0.30 pawns)
        book_move_bonuses = {}
        for move in moves:
            # Standard book move bonus: 25cp
            book_move_bonuses[move] = 25
            
        # The special move gets an extra 5cp (30cp total)
        if special_move:
            book_move_bonuses[special_move] = 30
            
        # Choose a suggested move based on probabilities
        suggested_move = None
        if moves:
            suggested_move = random.choices(moves, weights=probs, k=1)[0]
        
        result_info = {
            "book_move_bonuses": book_move_bonuses,
            "special_move": special_move,
            "all_book_moves": [m for m in moves]
        }
        
        return suggested_move, result_info
        
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
