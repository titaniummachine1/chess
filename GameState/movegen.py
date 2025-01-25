import chess
from GameState.drawback_manager import get_drawback_info

class DrawbackBoard(chess.Board):
    """
    A custom board class for Drawback Chess:
      - King capture => immediate game end.
      - Moving into check is allowed.
      - A drawback can restrict moves or cause auto-loss.
    """

    def __init__(self, fen=None, chess960=False):
        super().__init__(fen=fen, chess960=chess960)
        self.drawbacks = {chess.WHITE: None, chess.BLACK: None}

    def reset(self):
        """Resets the board and clears drawbacks."""
        super().reset()
        self.drawbacks = {chess.WHITE: None, chess.BLACK: None}

    def set_drawback(self, color, drawback_name):
        """Assign a named drawback to a specific player."""
        self.drawbacks[color] = drawback_name
        print(f"Set drawback for {'White' if color == chess.WHITE else 'Black'}: {drawback_name}")

    def get_active_drawback(self, color):
        """Returns the current drawback for the given color."""
        return self.drawbacks.get(color, None)

    # OVERRIDES to ignore check completely
    def checkers_mask(self):
        return 0

    def is_into_check(self, move):
        return False

    def was_into_check(self):
        return False

    @property
    def legal_moves(self):
        """Return drawback-filtered moves."""
        return self.generate_legal_moves()

    def generate_legal_moves(self, from_mask=chess.BB_ALL, to_mask=chess.BB_ALL):
        """Ensures AI and player moves respect drawbacks."""
        # Start with pseudo-legal moves (ignores check by default).
        moves = list(super().generate_pseudo_legal_moves(from_mask, to_mask))

        # If there's a drawback, filter out illegal moves.
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
        """The game ends if a king is missing or a drawback triggers a forced loss."""
        white_king_alive = any(piece.piece_type == chess.KING and piece.color == chess.WHITE for piece in self.piece_map().values())
        black_king_alive = any(piece.piece_type == chess.KING and piece.color == chess.BLACK for piece in self.piece_map().values())

        # If a king is missing => game ends
        if not white_king_alive or not black_king_alive:
            return True

        # Check if the current drawback triggers an auto-loss
        active_drawback = self.get_active_drawback(self.turn)
        if active_drawback:
            drawback_info = get_drawback_info(active_drawback)
            if drawback_info and "loss_condition" in drawback_info:
                loss_condition = drawback_info["loss_condition"]
                if callable(loss_condition) and loss_condition(self, self.turn):
                    print(f"Drawback '{active_drawback}' caused a loss!")
                    return True
        return False

    def is_variant_win(self):
        """If the opponent's king is missing => you win."""
        white_king_alive = any(piece.piece_type == chess.KING and piece.color == chess.WHITE for piece in self.piece_map().values())
        black_king_alive = any(piece.piece_type == chess.KING and piece.color == chess.BLACK for piece in self.piece_map().values())

        if not black_king_alive:
            return True  # White is the winner
        if not white_king_alive:
            return False # Black is the winner
        return False

    def is_variant_loss(self):
        """
        The current player loses if:
          - They have no legal moves,
          - Their own king is missing,
          - or a drawback triggers forced loss.
        """
        if self.is_variant_end():
            return not self.is_variant_win()

        # If no legal moves, that is a loss
        if not any(self.generate_legal_moves()):
            print(f"No moves left for {'White' if self.turn else 'Black'} => they lose.")
            return True
        return False

    def is_legal(self, move):
        """
        Checks if a move is legal ignoring check rules, but applying drawback-based restrictions.
        Also allows capturing the king.
        """
        # If it's in generate_legal_moves => it's legal
        if move in self.generate_legal_moves():
            return True

        # Special case: Pawn capturing the king forcibly allowed
        captured = self.piece_at(move.to_square)
        from_piece = self.piece_at(move.from_square)
        if captured and captured.piece_type == chess.KING and from_piece and from_piece.piece_type == chess.PAWN:
            return True

        return False

    def copy(self):
        """
        Makes a deep copy preserving the 'drawbacks' dictionary.
        """
        new_board = DrawbackBoard(fen=self.fen())
        new_board.drawbacks = self.drawbacks.copy()
        return new_board
