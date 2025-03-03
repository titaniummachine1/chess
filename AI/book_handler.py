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
        """Get book moves with bell curve distribution of weights"""
        # Get all book moves for current position
        book_moves = OPENING_BOOK.get_book_moves(board)
        print(f"BOOK DEBUG: Found {len(book_moves)} book moves for current position")
        
        if not book_moves:
            return None, {}
            
        # Print all available book moves with their weights
        print(f"BOOK DEBUG: Available moves: {', '.join([f'{move}:{weight}' for move, weight in book_moves])}")
        
        # Force new randomization each time - make sure to seed differently
        import time
        random.seed(time.time() + hash(board.fen()) % 1000)
        
        # Calculate move weights based on frequency
        total_freq = sum(freq for _, freq in book_moves)
        if total_freq == 0:
            return None, {}
            
        # Normalize frequencies to get probabilities
        move_probs = {}
        for move, freq in book_moves:
            # Add random variation (+/- 20%) to each probability for more diversity
            random_factor = 0.8 + 0.4 * random.random()  # 0.8 to 1.2
            normalized_prob = ((freq + 1) / (total_freq + len(book_moves))) * random_factor
            move_probs[move] = normalized_prob
        
        # Select 3-4 main book moves randomly with probability proportional to frequency
        num_main_moves = min(4, len(book_moves))
        if num_main_moves == 0:
            return None, {}
        
        # Check history of selected moves to avoid repetition
        position_key = board.fen().split(' ')[0]  # Use board position only
        if not hasattr(self, 'position_history'):
            self.position_history = {}
        
        position_hist = self.position_history.get(position_key, {})
        
        # Reduce probability for previously chosen moves
        for move in move_probs:
            if move in position_hist:
                # Penalize moves we've chosen before in this position
                move_probs[move] *= max(0.3, 1.0 - (position_hist[move] * 0.2))
                print(f"BOOK DEBUG: Adjusting probability of {move} due to history: {move_probs[move]:.4f}")
        
        # Selection logic
        # ... existing code for selecting weighted moves ...
        
        # Select main moves
        self.main_book_moves = []
        try:
            # Try to use numpy's choice for weighted selection
            moves_list = list(move_probs.keys())
            probs_list = list(move_probs.values())
            
            # Normalize probabilities to sum to 1
            probs_sum = sum(probs_list)
            if probs_sum > 0:
                probs_list = [p/probs_sum for p in probs_list]
            
            # Select moves with randomized weights
            main_indices = np.random.choice(
                len(moves_list), 
                size=num_main_moves, 
                replace=False, 
                p=probs_list
            )
            self.main_book_moves = [moves_list[i] for i in main_indices]
        except:
            # Fallback if numpy not available
            weighted_moves = []
            for move, prob in move_probs.items():
                weighted_moves.extend([move] * max(1, int(prob * 100)))
            
            selected = set()
            max_attempts = 100  # Prevent infinite loop
            attempts = 0
            while len(selected) < num_main_moves and weighted_moves and attempts < max_attempts:
                move = random.choice(weighted_moves)
                if move not in selected:
                    selected.add(move)
                attempts += 1
            
            self.main_book_moves = list(selected)
        
        # Create bell curve weights for PST adjustments
        bell_weights = {}
        
        # All main moves get top bell curve values (0.9-1.0) evenly distributed
        if self.main_book_moves:
            # Evenly distribute top main moves between 0.9-1.0
            top_range = 0.1  # range from 0.9 to 1.0
            step = top_range / len(self.main_book_moves) if len(self.main_book_moves) > 1 else 0.1
            
            # Add random variation to make bell curves unique each time
            for i, move in enumerate(self.main_book_moves):
                # Place each main move at an even interval on top of bell curve with small random variation
                variation = random.uniform(-0.02, 0.02)  # Small variation
                bell_weights[move] = min(1.0, 0.9 + (i * step) + variation)
                
                # Update position history for this move
                if position_key not in self.position_history:
                    self.position_history[position_key] = {}
                self.position_history[position_key][move] = self.position_history.get(position_key, {}).get(move, 0) + 1
        
        # Choose random move from main moves to highlight - different each time
        suggested_move = random.choice(self.main_book_moves) if self.main_book_moves else None
        
        # Print what we're choosing
        if suggested_move:
            print(f"BOOK DEBUG: Selected main moves: {[str(m) for m in self.main_book_moves]}")
            print(f"BOOK DEBUG: Primary suggestion: {suggested_move}, Weight: {bell_weights.get(suggested_move, 0):.4f}")
        
        # Return the suggested move and weights
        return suggested_move, {"weights": bell_weights, "default": 0.2}  # Low value for non-book moves
        
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
