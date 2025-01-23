import chess
from GameState.drawback_manager import get_drawback_info

class DrawbackBoard(chess.Board):
    """
    Custom board class for Drawback Chess:
      - Capturing the opponent's king => immediate win.
      - Moving into check is allowed (no forced resolution).
      - A drawback can further restrict moves or cause auto-loss.
    """

    def __init__(self, fen=None, chess960=False):
        super().__init__(fen, chess960=chess960)
        self.drawbacks = {chess.WHITE: None, chess.BLACK: None}

    def reset(self):
        """Resets the board and clears drawbacks."""
        super().reset()
        self.drawbacks = {chess.WHITE: None, chess.BLACK: None}

    def set_drawback(self, color, drawback_name):
        """Assign a named drawback to a specific color."""
        self.drawbacks[color] = drawback_name

    def get_active_drawback(self, color):
        """Returns the current drawback for the given color."""
        return self.drawbacks.get(color, None)

    @property
    def legal_moves(self):
        return self.generate_legal_moves()


    def is_variant_end(self):
        """Checks if the game ends: missing king or a drawback triggers loss."""
        white_king_alive = bool(self.kings & self.occupied_co[chess.WHITE])
        black_king_alive = bool(self.kings & self.occupied_co[chess.BLACK])
        # If a king is missing => game ends
        if not white_king_alive or not black_king_alive:
            return True
        # Check if the current player's drawback triggers an auto-loss
        active_drawback = self.get_active_drawback(self.turn)
        if active_drawback:
            drawback_info = get_drawback_info(active_drawback)
            if drawback_info and "loss_condition" in drawback_info:
                if drawback_info["loss_condition"](self, self.turn):
                    print(f"Drawback '{active_drawback}' caused a loss!")
                    return True
        return False

    def is_variant_win(self):
        """
        A player wins if the opponent's king is missing:
        - If black's king is gone => White wins,
        - If white's king is gone => Black wins.
        """
        white_king_alive = bool(self.kings & self.occupied_co[chess.WHITE])
        black_king_alive = bool(self.kings & self.occupied_co[chess.BLACK])
        if not black_king_alive:
            return True   # White is the winner
        if not white_king_alive:
            return False  # Black is the winner
        return False

    def is_variant_loss(self):
        """
        The current player loses if they've no king or a drawback triggers loss,
        but they aren't the winner.
        """
        return self.is_variant_end() and not self.is_variant_win()

    def generate_legal_moves(self, from_mask=chess.BB_ALL, to_mask=chess.BB_ALL):
        """
        1) If game is lost, yield no moves.
        2) Generate pseudo-legal moves (ignoring check).
        3) Filter them by the active drawback's "illegal_moves" if any.
        """
        if self.is_variant_loss():
            return iter([])

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
                        print(f"Blocked by '{active_drawback}': {m}")
                moves = filtered

        return iter(moves)

    def is_legal(self, move):
        """
        If a move is in generate_pseudo_legal_moves() and not blocked by
        the active drawback, it's legal. King captures are always legal.
        """
        # Must be pseudo-legal
        if move not in super().generate_pseudo_legal_moves():
            return False
        # King capture is always allowed
        captured_piece = self.piece_at(move.to_square)
        if captured_piece and captured_piece.piece_type == chess.KING:
            return True
        # Check active drawback
        active_drawback = self.get_active_drawback(self.turn)
        if active_drawback:
            drawback_info = get_drawback_info(active_drawback)
            if drawback_info and "illegal_moves" in drawback_info:
                if drawback_info["illegal_moves"](self, self.turn, move):
                    return False
        return True