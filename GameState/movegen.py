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

    def is_variant_end(self):
        """
        The game ends if:
          - One side's king is gone (the other side wins),
          - or a drawback triggers an immediate loss.
        """
        # 1) Check if either king is missing
        white_king_alive = bool(self.kings & self.occupied_co[chess.WHITE])
        black_king_alive = bool(self.kings & self.occupied_co[chess.BLACK])

        if not white_king_alive or not black_king_alive:
            # The game ends immediately if one king is gone
            return True

        # 2) Check if the current player's drawback triggers a loss
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
        A player wins if the *opponent’s* king is missing.
        That is:
          - If black king is missing => White wins,
          - If white king is missing => Black wins.
        """
        white_king_alive = bool(self.kings & self.occupied_co[chess.WHITE])
        black_king_alive = bool(self.kings & self.occupied_co[chess.BLACK])

        if not black_king_alive:
            # Opponent's (Black) king is missing => White is the winner
            return True
        if not white_king_alive:
            # Opponent's (White) king is missing => Black is the winner
            return False  # White's missing => for White's perspective, that's a loss

        # Otherwise, no winner yet
        return False

    def is_variant_loss(self):
        """
        The current player loses if their own king is missing
        or if a drawback triggers a loss (handled by is_variant_end()) 
        but they are *not* the winner.
        """
        return self.is_variant_end() and not self.is_variant_win()

    def generate_legal_moves(self, from_mask=chess.BB_ALL, to_mask=chess.BB_ALL):
        """
        Generates legal moves ignoring check. Also filters out moves by the current drawback.
        """
        # If the game is already over, yield no moves
        if self.is_variant_end():
            return iter([])

        # 1) Generate all standard moves ignoring check (pseudo_legal or normal legal):
        #    - Since we want to allow moving into check, let's use pseudo-legal:
        legal_moves = list(super().generate_pseudo_legal_moves(from_mask, to_mask))

        # 2) Filter out moves restricted by the current player's drawback
        active_drawback = self.get_active_drawback(self.turn)
        if active_drawback:
            drawback_info = get_drawback_info(active_drawback)
            if drawback_info and "illegal_moves" in drawback_info:
                # Keep only the moves that are not declared illegal
                legal_moves = [m for m in legal_moves if not drawback_info["illegal_moves"](self, self.turn, m)]

        return iter(legal_moves)

    def is_legal(self, move):
        """
        Determines if a move is legal:
          - Allows capturing the king,
          - Ignores check rules,
          - Respects any drawback-based restrictions.
        """
        # Must be a valid (pseudo-legal) chess move
        if move not in super().generate_pseudo_legal_moves():
            return False

        # If the move captures a king, it's allowed
        if self.piece_at(move.to_square) and self.piece_at(move.to_square).piece_type == chess.KING:
            return True

        # Otherwise, respect the active drawback
        active_drawback = self.get_active_drawback(self.turn)
        if active_drawback:
            drawback_info = get_drawback_info(active_drawback)
            if drawback_info and "illegal_moves" in drawback_info:
                # If the drawback says it's illegal, then it's not legal
                if drawback_info["illegal_moves"](self, self.turn, move):
                    return False

        return True
