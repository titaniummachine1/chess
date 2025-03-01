from enum import Enum
import numpy as np
import chess
from GameState.movegen import DrawbackBoard
from GameState.drawback_manager import get_drawback_info

class Score(Enum):
    """Defines piece values and game evaluation constants."""
    PAWN = np.int32(100)
    KNIGHT = np.int32(300)
    BISHOP = np.int32(300)
    ROOK = np.int32(500)
    QUEEN = np.int32(900)
    KING = np.int32(20000)  # Extremely high value to make king capture an absolute priority
    CHECKMATE = np.int32(100000)  # Winning state
    MOVE = np.int32(5)  # Mobility bonus

# Standard piece values
PIECE_VALUES = {
    chess.PAWN: 100,
    chess.KNIGHT: 320,
    chess.BISHOP: 330,
    chess.ROOK: 500,
    chess.QUEEN: 900,
    chess.KING: 20000  # Making king worth much more to prioritize its capture
}

class Evaluator:
    """Class for handling board evaluation with dependency injection for piece square tables."""
    
    def __init__(self, piece_square_tables=None):
        """
        Initialize the evaluator with optional piece square tables.
        
        Args:
            piece_square_tables: An object providing piece square table functionality
        """
        self.piece_square_tables = piece_square_tables
    
    def evaluate_board(self, board):
        """
        Complete board evaluation incorporating all evaluation components.
        
        Args:
            board: A chess board position to evaluate
            
        Returns:
            An integer score from the perspective of the side to move
        """
        # Check for terminal positions (king capture)
        terminal_score = self._check_terminal_position(board)
        if terminal_score is not None:
            return terminal_score
            
        # Main evaluation components
        material_score = self._eval_material(board)
        mobility_score = self._eval_mobility(board)
        positional_score = self._eval_positional(board)
        drawback_score = self._eval_drawback_specific(board)
        king_safety_score = self._eval_king_safety(board) * 2  # Apply king safety factor
        
        # Add piece square table evaluation if available
        pst_score = 0
        if self.piece_square_tables:
            pst_score = self._eval_piece_square_tables(board)
            
        # Combine all evaluation components
        total_score = (
            material_score + 
            mobility_score + 
            positional_score + 
            drawback_score + 
            king_safety_score +
            pst_score
        )
        
        return total_score
    
    def _check_terminal_position(self, board):
        """Check for terminal positions like king captures."""
        # Check for king capture (immediate win/loss situation)
        white_king_alive = any(piece.piece_type == chess.KING and piece.color == chess.WHITE 
                              for piece in board.piece_map().values())
        black_king_alive = any(piece.piece_type == chess.KING and piece.color == chess.BLACK 
                              for piece in board.piece_map().values())
        
        if not black_king_alive:
            return Score.CHECKMATE.value  # White wins by capturing the Black king
        if not white_king_alive:
            return -Score.CHECKMATE.value  # Black wins by capturing the White king
            
        # If no legal moves, it's usually a losing position
        if hasattr(board, "is_variant_loss") and board.is_variant_loss():
            return -Score.CHECKMATE.value
            
        return None  # Not a terminal position
    
    def get_piece_value(self, board, piece_type, color):
        """
        Returns the value of a piece, modified by drawbacks if applicable.
        - If a drawback affects a piece's value, use the drawback's override
        - Otherwise, use the standard value
        """
        # Special case for kings - always keep them valuable
        if piece_type == chess.KING:
            return PIECE_VALUES[chess.KING]
            
        # Check if the board supports drawbacks
        if hasattr(board, "get_active_drawback"):
            active_drawback = board.get_active_drawback(color)
            
            # Apply drawback modification if applicable
            if active_drawback:
                drawback_info = get_drawback_info(active_drawback)
                if drawback_info and "piece_value_override" in drawback_info:
                    override_value = drawback_info["piece_value_override"].get(piece_type)
                    if override_value is not None:
                        return override_value
        
        return PIECE_VALUES.get(piece_type, 0)
    
    def _eval_material(self, board):
        """Evaluates material balance between White and Black, considering drawbacks."""
        material = 0
        
        for piece_type in [chess.PAWN, chess.KNIGHT, chess.BISHOP, chess.ROOK, chess.QUEEN, chess.KING]:
            white_count = sum(1 for piece in board.piece_map().values() 
                             if piece.color == chess.WHITE and piece.piece_type == piece_type)
            black_count = sum(1 for piece in board.piece_map().values() 
                             if piece.color == chess.BLACK and piece.piece_type == piece_type)
                             
            white_value = white_count * self.get_piece_value(board, piece_type, chess.WHITE)
            black_value = black_count * self.get_piece_value(board, piece_type, chess.BLACK)
            
            material += white_value - black_value
            
        # Adjust perspective based on side to move
        if board.turn == chess.BLACK:
            material = -material
            
        return material
    
    def _eval_mobility(self, board):
        """
        Evaluates mobility. More legal moves = better position.
        If the player has no moves and the king is in danger, they're likely to lose soon.
        """
        num_moves = len(list(board.legal_moves))
        
        if num_moves == 0:
            # In Drawback Chess, having no moves isn't an immediate loss,
            # but it's still very bad
            return -Score.CHECKMATE.value // 2
            
        return Score.MOVE.value * np.int32(num_moves)
    
    def _eval_positional(self, board):
        """
        Evaluates piece placement using basic positional principles.
        - Encourages control of the center (D4, D5, E4, E5).
        - Applies any drawback-based positional penalties or bonuses.
        """
        score = 0
        
        # Center control bonus
        central_squares = [chess.D4, chess.D5, chess.E4, chess.E5]
        
        for square, piece in board.piece_map().items():
            piece_value = self.get_piece_value(board, piece.piece_type, piece.color)
            
            # Skip if piece has 0 value due to drawback
            if piece_value == 0:
                continue
                
            # Default positional bonus (encourage center control)
            positional_value = 5 if square in central_squares else 0
            
            # Adjust score based on piece color and side to move
            if piece.color == board.turn:
                score += positional_value
            else:
                score -= positional_value
                
        return score
    
    def _eval_drawback_specific(self, board):
        """
        Apply specific evaluation bonuses/penalties based on the active drawbacks.
        """
        # Skip if board doesn't support drawbacks
        if not hasattr(board, "get_active_drawback"):
            return 0
            
        score = 0
        
        # Get drawbacks for both players
        white_drawback = board.get_active_drawback(chess.WHITE)
        black_drawback = board.get_active_drawback(chess.BLACK)
        
        # Check for strategic advantages based on drawbacks
        if board.turn == chess.WHITE:
            # White is playing
            
            # If White has no knight moves, encourage pawn advancement and bishop development
            if white_drawback == "no_knight_moves":
                # Count advanced pawns and developed bishops
                for square, piece in board.piece_map().items():
                    if piece.color == chess.WHITE:
                        rank = chess.square_rank(square)
                        if piece.piece_type == chess.PAWN and rank >= 3:  # Pawn advanced to rank 4 or beyond
                            score += 5
                        elif piece.piece_type == chess.BISHOP and rank >= 2:  # Bishop developed
                            score += 10
            
            # If White has punching down restriction, prioritize protecting valuable pieces
            elif white_drawback == "punching_down":
                # Bonus for having pawns near valuable pieces
                for square, piece in board.piece_map().items():
                    if piece.color == chess.WHITE and piece.piece_type in [chess.QUEEN, chess.ROOK]:
                        # Check for pawn protection
                        piece_rank = chess.square_rank(square)
                        piece_file = chess.square_file(square)
                        # Look for pawns that can protect this piece
                        for pawn_offset in [(-1, -1), (-1, 1)]:  # Diagonal squares a pawn would defend from
                            pr, pf = piece_rank + pawn_offset[0], piece_file + pawn_offset[1]
                            if 0 <= pr < 8 and 0 <= pf < 8:
                                pawn_sq = chess.square(pf, pr)
                                pawn = board.piece_at(pawn_sq)
                                if pawn and pawn.piece_type == chess.PAWN and pawn.color == chess.WHITE:
                                    score += 15  # Bonus for having a pawn protecting valuable piece
            
            # If Black can't capture with knights or bishops, that's an advantage for White
            if black_drawback in ["no_knight_captures", "no_bishop_captures"]:
                score += 15  # Generic bonus for opponent's capture restriction
                
            # If Black has "punching down", White should prioritize exposing their queen
            if black_drawback == "punching_down":
                # Look for opportunities to attack with queen
                for square, piece in board.piece_map().items():
                    if piece.color == chess.WHITE and piece.piece_type == chess.QUEEN:
                        # Bonus for queen mobility - number of squares it can move to
                        queen_mobility = sum(1 for move in board.legal_moves 
                                             if move.from_square == square)
                        score += queen_mobility * 2  # Each mobility square is worth 2 points
                
        else:
            # Black is playing - similar logic with colors reversed
            if black_drawback == "no_knight_moves":
                for square, piece in board.piece_map().items():
                    if piece.color == chess.BLACK:
                        rank = chess.square_rank(square)
                        if piece.piece_type == chess.PAWN and rank <= 4:  # Pawn advanced to rank 5 or beyond
                            score += 5
                        elif piece.piece_type == chess.BISHOP and rank <= 5:  # Bishop developed
                            score += 10
            
            elif black_drawback == "punching_down":
                for square, piece in board.piece_map().items():
                    if piece.color == chess.BLACK and piece.piece_type in [chess.QUEEN, chess.ROOK]:
                        piece_rank = chess.square_rank(square)
                        piece_file = chess.square_file(square)
                        for pawn_offset in [(1, -1), (1, 1)]:
                            pr, pf = piece_rank + pawn_offset[0], piece_file + pawn_offset[1]
                            if 0 <= pr < 8 and 0 <= pf < 8:
                                pawn_sq = chess.square(pf, pr)
                                pawn = board.piece_at(pawn_sq)
                                if pawn and pawn.piece_type == chess.PAWN and pawn.color == chess.BLACK:
                                    score += 15
            
            if white_drawback in ["no_knight_captures", "no_bishop_captures"]:
                score += 15
            
            if white_drawback == "punching_down":
                for square, piece in board.piece_map().items():
                    if piece.color == chess.BLACK and piece.piece_type == chess.QUEEN:
                        queen_mobility = sum(1 for move in board.legal_moves 
                                             if move.from_square == square)
                        score += queen_mobility * 2
        
        return score
    
    def _eval_king_safety(self, board):
        """
        Evaluates king safety by counting the number of friendly pawns around each king.
        More friendly pawn cover yields a higher safety bonus.
        This bonus is subtracted for the opponent.
        """
        safety_score = 0
        offsets = [(-1,-1), (-1,0), (-1,1), (0,-1), (0,1), (1,-1), (1,0), (1,1)]
        
        for color in [chess.WHITE, chess.BLACK]:
            king_sq = None
            for square, piece in board.piece_map().items():
                if piece.piece_type == chess.KING and piece.color == color:
                    king_sq = square
                    break
                    
            if king_sq is None:
                continue  # Should be handled as terminal elsewhere
                
            pawn_cover = 0
            king_file = chess.square_file(king_sq)
            king_rank = chess.square_rank(king_sq)
            
            for dx, dy in offsets:
                new_file = king_file + dx
                new_rank = king_rank + dy
                if 0 <= new_file < 8 and 0 <= new_rank < 8:
                    sq = chess.square(new_file, new_rank)
                    neighbor = board.piece_at(sq)
                    if neighbor and neighbor.piece_type == chess.PAWN and neighbor.color == color:
                        pawn_cover += 1
                        
            bonus = pawn_cover * 10  # Each pawn adds 10 points
            
            # Add bonus for the side whose turn it is; subtract for opponent
            if color == board.turn:
                safety_score += bonus
            else:
                safety_score -= bonus
                
        return safety_score
    
    def _eval_piece_square_tables(self, board):
        """
        Evaluates the position using piece-square tables.
        Requires self.piece_square_tables to be set.
        """
        if not self.piece_square_tables:
            return 0
            
        score = 0
        phase = self.piece_square_tables.compute_game_phase(board)
        
        for square, piece in board.piece_map().items():
            piece_symbol = piece.symbol().upper()
            
            # Use the piece-square table module's interpolation function
            piece_square_value = self.piece_square_tables.interpolate_piece_square(
                piece_symbol, square, piece.color, board
            )
            
            # Adjust the score based on piece color
            if piece.color == chess.WHITE:
                score += piece_square_value
            else:
                score -= piece_square_value
                
        # Adjust for whose turn it is
        if board.turn == chess.BLACK:
            score = -score
            
        return score

# Legacy function that uses the Evaluator class with default settings
def evaluate_board(board):
    """Legacy function to maintain backward compatibility."""
    evaluator = Evaluator()
    return evaluator.evaluate_board(board)

# Legacy function that uses the Evaluator class with default settings
def evaluate(board):
    """Legacy function to maintain backward compatibility."""
    evaluator = Evaluator()
    return evaluator.evaluate_board(board)