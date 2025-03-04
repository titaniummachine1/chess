## movegen.py contains the custom board class for Drawback Chess, which extends the standard python-chess board class.
import chess
import random
from GameState.drawback_manager import DRAWBACKS, get_drawback_info, get_drawback_function, get_drawback_loss_function

# Correct standard FEN with the king and queen in their proper places
defaultfen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"

class DrawbackBoard(chess.Board):
    """
    A custom board class for Drawback Chess:
      - Standard starting FEN (white on bottom, black on top).
      - Ignores checks, can capture king.
      - Drawback-based restrictions.
    """

    def __init__(self, fen=chess.STARTING_FEN, white_drawback=None, black_drawback=None):
        super().__init__(fen)
        self._white_drawback = white_drawback
        self._black_drawback = black_drawback
        print(f"DrawbackBoard initialized with white_drawback={white_drawback}, black_drawback={black_drawback}")

    def reset(self, fen=chess.STARTING_FEN):
        """Reset the board to the starting position"""
        super().reset()
        self._white_drawback = None
        self._black_drawback = None

    def set_white_drawback(self, drawback):
        """Set the white drawback"""
        self._white_drawback = drawback

    def set_black_drawback(self, drawback):
        """Set the black drawback"""
        self._black_drawback = drawback

    def get_active_drawback(self, color):
        """Get the active drawback for the specified color"""
        if color == chess.WHITE:
            return self._white_drawback
        else:
            return self._black_drawback

    # Ignore checks entirely
    def checkers_mask(self):
        return 0

    def is_into_check(self, move):
        return False

    def was_into_check(self):
        return False

    @property
    def legal_moves(self):
        return self.generate_legal_moves()

    def generate_legal_moves(self, from_mask=chess.BB_ALL, to_mask=chess.BB_ALL):
        """Generate legal moves considering drawbacks"""
        # Get standard chess moves first
        moves = list(super().generate_pseudo_legal_moves(from_mask, to_mask))
        
        # Apply drawback restrictions
        active_drawback = self.get_active_drawback(self.turn)
        if active_drawback:
            print(f"Filtering moves for {self.turn} with drawback: {active_drawback}")
            filtered_moves = []
            for move in moves:
                if self._check_drawbacks(move, self.turn):
                    filtered_moves.append(move)
                else:
                    print(f"Drawback '{active_drawback}' blocked move: {move}")
            return iter(filtered_moves)
                
        return iter(moves)

    def is_variant_end(self):
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
                print(f"Drawback '{active_drawback}' triggered loss condition!")
                return True
                    
        # No other end conditions - you must capture the king to win
        return False

    def is_variant_win(self):
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

    def is_variant_loss(self):
        """
        In Drawback Chess, you lose when your king is captured.
        Having no legal moves doesn't mean you lose - the opponent must capture your king.
        """
        if self.is_variant_end():
            return not self.is_variant_win()
            
        # Special case: if there are no legal moves but the game isn't over,
        # we don't consider it a loss yet - the opponent must capture the king
        return False

    def is_legal(self, move):
        """Enhanced is_legal that incorporates drawback rules"""
        # Basic legality check first
        if not super().is_legal(move):
            return False
            
        # Check drawbacks for the current player
        return self._check_drawbacks(move, self.turn)
        
    def _check_drawbacks(self, move, color):
        """Check if a move is legal according to active drawbacks"""
        drawback_name = self.get_active_drawback(color)
        if not drawback_name:
            return True
            
        # Get check function for this drawback
        check_function = get_drawback_function(drawback_name)
        if not check_function:
            print(f"WARNING: No check function found for drawback '{drawback_name}'")
            return True  # Allow move if drawback function is missing
        
        try:
            # Get drawback parameters if any
            drawback_info = get_drawback_info(drawback_name)
            params = drawback_info.get("params", {})
            
            # Call the check function with parameters
            if params:
                result = check_function(self, move, color, **params)
            else:
                result = check_function(self, move, color)
            
            # Log result for debugging
            if not result:
                print(f"Drawback '{drawback_name}' rejected move {move}")
                
            return result
            
        except Exception as e:
            print(f"Error checking drawback {drawback_name}: {e}")
            import traceback
            traceback.print_exc()
            return True  # Allow move if there's an error

    def copy(self):
        new_board = DrawbackBoard(fen=self.fen())
        new_board._white_drawback = self._white_drawback
        new_board._black_drawback = self._black_drawback
        return new_board
