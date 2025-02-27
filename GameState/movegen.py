## movegen.py contains the custom board class for Drawback Chess, which extends the standard python-chess board class. do nto remove this comment
import chess
from GameState.drawback_manager import get_drawback_info

# Correct standard FEN with the king and queen in their proper places
defaultfen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"

class DrawbackBoard(chess.Board):
    """
    A custom board class for Drawback Chess:
      - Standard starting FEN (white on bottom, black on top).
      - Ignores checks, can capture king.
      - Drawback-based restrictions.
    """

    def __init__(self, fen=None):
        # Always start standard
        if fen is None:
            fen = defaultfen
        super().__init__(fen=fen)

        # Store drawbacks for each color
        self.drawbacks = {chess.WHITE: None, chess.BLACK: None}

    def reset(self):
        """Resets the board to the standard starting position and clears drawbacks."""
        super().set_fen(defaultfen)
        self.drawbacks = {chess.WHITE: None, chess.BLACK: None}

    def set_drawback(self, color, drawback_name):
        self.drawbacks[color] = drawback_name
        print(f"Set drawback for {'White' if color == chess.WHITE else 'Black'}: {drawback_name}")

    def get_active_drawback(self, color):
        return self.drawbacks.get(color, None)

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
        moves = list(super().generate_pseudo_legal_moves(from_mask, to_mask))

        active_drawback = self.get_active_drawback(self.turn)
        if active_drawback:
            drawback_info = get_drawback_info(active_drawback)
            if drawback_info and "illegal_moves" in drawback_info:
                filtered = []
                for m in moves:
                    if not drawback_info["illegal_moves"](self, self.turn, m):
                        filtered.append(m)
                    # Only show blocked move in detailed debugging
                    # else:
                    #     print(f"Drawback '{active_drawback}' blocked move: {m}")
                moves = filtered
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
            drawback_info = get_drawback_info(active_drawback)
            if drawback_info and "loss_condition" in drawback_info:
                condition = drawback_info["loss_condition"]
                if callable(condition) and condition(self, self.turn):
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
        """Check if a move is legal, with Drawback Chess special rules"""
        # Normal legal moves from our generator
        if move in self.generate_legal_moves():
            return True

        # Special case: allow capturing the king
        captured = self.piece_at(move.to_square)
        if captured and captured.piece_type == chess.KING:
            from_piece = self.piece_at(move.from_square)
            if from_piece and from_piece.color != captured.color:
                # Ensure move is otherwise valid (no drawback restrictions)
                active_drawback = self.get_active_drawback(self.turn)
                if active_drawback:
                    drawback_info = get_drawback_info(active_drawback)
                    if drawback_info and "illegal_moves" in drawback_info:
                        if drawback_info["illegal_moves"](self, self.turn, move):
                            return False  # Drawback blocks this move
                return True  # King capture is allowed

        return False

    def copy(self):
        new_board = DrawbackBoard(fen=self.fen())
        new_board.drawbacks = self.drawbacks.copy()
        return new_board
