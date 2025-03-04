## movegen.py contains the custom board class for Drawback Chess, which extends the standard python-chess board class.
import chess
import random
from typing import Iterator, Optional, List, Union
from GameState.drawback_manager import (
    get_drawback_info, get_drawback_function, get_drawback_loss_function
)

class DrawbackBoard(chess.Board):
    """
    A custom board class for Drawback Chess:
      - Standard starting FEN (white on bottom, black on top).
      - Ignores checks, can capture king.
      - Drawback-based restrictions.
    """

    def __init__(self, fen: str = chess.STARTING_FEN, white_drawback: Optional[str] = None, black_drawback: Optional[str] = None):
        super().__init__(fen)
        self._white_drawback = white_drawback
        self._black_drawback = black_drawback

    def reset(self, fen: str = chess.STARTING_FEN) -> None:
        """Reset the board to the starting position"""
        super().reset()
        self._white_drawback = None
        self._black_drawback = None

    def set_white_drawback(self, drawback: Optional[str]) -> None:
        """Set the white drawback"""
        self._white_drawback = drawback

    def set_black_drawback(self, drawback: Optional[str]) -> None:
        """Set the black drawback"""
        self._black_drawback = drawback

    def get_active_drawback(self, color: chess.Color) -> Optional[str]:
        """Get the active drawback for the specified color"""
        assert color in [chess.WHITE, chess.BLACK], "Invalid color"
        return self._white_drawback if color == chess.WHITE else self._black_drawback

    # Ignore checks entirely
    def checkers_mask(self) -> chess.Bitboard:
        return 0

    def is_into_check(self, move: chess.Move) -> bool:
        return False

    def was_into_check(self) -> bool:
        return False

    @property
    def legal_moves(self) -> Iterator[chess.Move]:
        return self.generate_legal_moves()

    def generate_legal_moves(self, from_mask: chess.Bitboard = chess.BB_ALL, to_mask: chess.Bitboard = chess.BB_ALL) -> Iterator[chess.Move]:
        """Generate legal moves considering drawbacks"""
        # Get standard chess moves first
        moves = list(super().generate_pseudo_legal_moves(from_mask, to_mask))
        
        # Apply drawback restrictions
        active_drawback = self.get_active_drawback(self.turn)
        if active_drawback:
            filtered_moves = []
            for move in moves:
                if self._check_drawbacks(move, self.turn):
                    filtered_moves.append(move)
            return iter(filtered_moves)
                
        return iter(moves)

    def is_variant_end(self) -> bool:
        """
        In Drawback Chess, the game ends when one of the kings is captured.
        """
        white_king_alive = any(p.piece_type == chess.KING and p.color == chess.WHITE
                               for p in self.piece_map().values())
        black_king_alive = any(p.piece_type == chess.KING and p.color == chess.BLACK
                               for p in self.piece_map().values())

        # Game ends when a king is captured
        if not white_king_alive or not black_king_alive:
            return True

        # Check for special drawback-related loss conditions
        active_drawback = self.get_active_drawback(self.turn)
        if active_drawback:
            loss_function = get_drawback_loss_function(active_drawback)
            if loss_function and loss_function(self, self.turn):
                return True
                    
        # No other end conditions - you must capture the king to win
        return False

    def is_variant_win(self) -> bool:
        """
        In Drawback Chess, you win by capturing the opponent's king.
        """
        white_king_alive = any(p.piece_type == chess.KING and p.color == chess.WHITE
                               for p in self.piece_map().values())
        black_king_alive = any(p.piece_type == chess.KING and p.color == chess.BLACK
                               for p in self.piece_map().values())

        # White wins if Black's king is captured
        if not black_king_alive:
            return True
        # Black wins if White's king is captured    
        if not white_king_alive:
            return False
            
        # No win yet if both kings are alive
        return False

    def is_variant_loss(self) -> bool:
        """
        In Drawback Chess, you lose when your king is captured.
        Having no legal moves doesn't mean you lose - the opponent must capture your king.
        """
        if self.is_variant_end():
            return not self.is_variant_win()
            
        # Special case: if there are no legal moves but the game isn't over,
        # we don't consider it a loss yet - the opponent must capture the king
        return False

    def is_legal(self, move: chess.Move) -> bool:
        """Enhanced is_legal that incorporates drawback rules"""
        # Basic legality check first
        if not super().is_legal(move):
            return False
            
        # Check drawbacks for the current player
        return self._check_drawbacks(move, self.turn)
        
    def _check_drawbacks(self, move: chess.Move, color: chess.Color) -> bool:
        """Check if a move is legal according to active drawbacks"""
        drawback_name = self.get_active_drawback(color)
        if not drawback_name:
            return True
            
        try:
            # Get check function for this drawback
            check_function = get_drawback_function(drawback_name)
            if not check_function:
                print(f"WARNING: No check function found for drawback '{drawback_name}'")
                return True  # Default to allowing the move if function not found
            
            # Get drawback parameters if any
            drawback_info = get_drawback_info(drawback_name)
            params = drawback_info.get("params", {})
            
            # Try the function with standard parameter order
            try:
                # Standard order: (board, move, color)
                result = check_function(self, move, color, **params) if params else check_function(self, move, color)
                return not result  # Invert result (True means illegal, we return False for illegal)
            except TypeError as e:
                # If that fails, try alternate parameter order: (board, color, move)
                print(f"WARNING: Primary parameter order failed for {drawback_name}: {e}")
                try:
                    result = check_function(self, color, move, **params) if params else check_function(self, color, move)
                    print(f"Alternate parameter order worked for {drawback_name}")
                    return not result  # Invert result (True means illegal, we return False for illegal)
                except Exception as inner_e:
                    print(f"ERROR: Both parameter orders failed for {drawback_name}: {inner_e}")
                    return True  # Default to allowing moves on error
                
        except Exception as e:
            print(f"ERROR checking drawback '{drawback_name}': {e}")
            import traceback
            traceback.print_exc()
            return True  # Default to allowing the move on error

    def copy(self) -> 'DrawbackBoard':
        new_board = DrawbackBoard(fen=self.fen())
        new_board._white_drawback = self._white_drawback
        new_board._black_drawback = self._black_drawback
        return new_board
