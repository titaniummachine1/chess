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
                    else:
                        print(f"Drawback '{active_drawback}' blocked move: {m}")
                moves = filtered
        return iter(moves)

    def is_variant_end(self):
        white_king_alive = any(p.piece_type == chess.KING and p.color == chess.WHITE
                               for p in self.piece_map().values())
        black_king_alive = any(p.piece_type == chess.KING and p.color == chess.BLACK
                               for p in self.piece_map().values())

        if not white_king_alive or not black_king_alive:
            return True

        active_drawback = self.get_active_drawback(self.turn)
        if active_drawback:
            drawback_info = get_drawback_info(active_drawback)
            if drawback_info and "loss_condition" in drawback_info:
                condition = drawback_info["loss_condition"]
                if callable(condition) and condition(self, self.turn):
                    print(f"Drawback '{active_drawback}' caused a loss!")
                    return True
        return False

    def is_variant_win(self):
        white_king_alive = any(p.piece_type == chess.KING and p.color == chess.WHITE
                               for p in self.piece_map().values())
        black_king_alive = any(p.piece_type == chess.KING and p.color == chess.BLACK
                               for p in self.piece_map().values())

        if not black_king_alive:
            return True  # White is the winner
        if not white_king_alive:
            return False # Black is the winner
        return False

    def is_variant_loss(self):
        if self.is_variant_end():
            return not self.is_variant_win()

        if not any(self.generate_legal_moves()):
            print(f"No moves left for {'White' if self.turn == chess.WHITE else 'Black'} => they lose.")
            return True
        return False

    def is_legal(self, move):
        if move in self.generate_legal_moves():
            return True

        # Pawn capturing the king forcibly allowed
        captured = self.piece_at(move.to_square)
        from_piece = self.piece_at(move.from_square)
        if (captured
            and captured.piece_type == chess.KING
            and from_piece
            and from_piece.piece_type == chess.PAWN):
            return True

        return False

    def copy(self):
        new_board = DrawbackBoard(fen=self.fen())
        new_board.drawbacks = self.drawbacks.copy()
        return new_board
