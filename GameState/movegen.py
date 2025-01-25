import chess
from GameState.drawback_manager import get_drawback_info

class DrawbackBoard(chess.Board):
    """
    A custom board class for Drawback Chess:
      - Capturing the opponent's king => immediate game end.
      - Moving into check is allowed (no forced resolution).
      - A drawback can further restrict moves or cause auto-loss.
    """

    def __init__(self, fen=None, chess960=False):
        super().__init__(fen=fen, chess960=chess960)
        self.drawbacks = {chess.WHITE: None, chess.BLACK: None}

    def reset(self):
        """
        Resets the board and clears drawbacks.
        """
        super().reset()
        self.drawbacks = {chess.WHITE: None, chess.BLACK: None}

    def set_drawback(self, color, drawback_name):
        """
        Assign a named drawback to a specific player.
        """
        if color not in [chess.WHITE, chess.BLACK]:
            raise ValueError("Invalid color for drawback assignment.")
        self.drawbacks[color] = drawback_name
        print(f"Set drawback for {'White' if color == chess.WHITE else 'Black'}: {drawback_name}")

    def get_active_drawback(self, color):
        """
        Returns the current drawback for the given color.
        """
        return self.drawbacks.get(color, None)

    @property
    def legal_moves(self):
        """
        Overrides chess.Board.legal_moves to return drawback-filtered moves.
        """
        return self.generate_legal_moves()

    def is_variant_end(self):
        """
        Checks if the game ends:
          - If a king is missing, or
          - A drawback triggers an immediate loss.
        """
        white_king_alive = bool(self.kings & self.occupied_co[chess.WHITE])
        black_king_alive = bool(self.kings & self.occupied_co[chess.BLACK])

        # End if either king is missing
        if not white_king_alive or not black_king_alive:
            return True

        # Check if the current player's drawback triggers an auto-loss
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
        """
        A player wins if the opponent's king is missing:
         - If black's king is gone => White wins
         - If white's king is gone => Black wins
        """
        white_king_alive = bool(self.kings & self.occupied_co[chess.WHITE])
        black_king_alive = bool(self.kings & self.occupied_co[chess.BLACK])

        if not black_king_alive:
            return True
        if not white_king_alive:
            return False
        return False

    def is_variant_loss(self):
        """
        The current player loses if:
         - They have no legal moves, or
         - Their own king is missing, or
         - A drawback triggers a loss.
        """
        if self.is_variant_end():
            return not self.is_variant_win()

        # If the player has no legal moves, they lose
        if not self._has_any_legal_move():
            print(f"{'White' if self.turn == chess.WHITE else 'Black'} has no legal moves and loses!")
            return True

        return False

    def _has_any_legal_move(self):
        """
        Checks if the current player has any legal moves without calling generate_legal_moves
        (to avoid recursion).
        Instead, it manually filters pseudo-legal moves with drawback rules.
        """
        active_drawback = self.get_active_drawback(self.turn)

        for move in super().generate_pseudo_legal_moves():
            # If there's a drawback, check if this move is blocked
            if active_drawback:
                info = get_drawback_info(active_drawback)
                if info and "illegal_moves" in info:
                    if info["illegal_moves"](self, self.turn, move):
                        continue  # This move is blocked, skip it

            # Pawn capturing a king forcibly allowed
            captured = self.piece_at(move.to_square)
            if captured and captured.piece_type == chess.KING:
                from_piece = self.piece_at(move.from_square)
                if from_piece and from_piece.piece_type == chess.PAWN:
                    return True

            # If we get here, the move is valid
            return True

        # Also check forced pawn-king captures not recognized by standard rules
        forced = self._force_pawn_king_captures()
        for move in forced:
            if active_drawback:
                info = get_drawback_info(active_drawback)
                if info and "illegal_moves" in info:
                    if info["illegal_moves"](self, self.turn, move):
                        continue
            return True

        # No valid move found
        return False

    def generate_legal_moves(self, from_mask=chess.BB_ALL, to_mask=chess.BB_ALL):
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
                        assert drawback_info["illegal_moves"](self, self.turn, m), f"Move {m} should be blocked by drawback {active_drawback}"
                moves = filtered

        return iter(moves)

    def is_legal(self, move):
        """
        Checks if a move is legal, ignoring check rules but applying drawback restrictions.
        - King captures are always allowed.
        - Pawn capturing king is forcibly allowed.
        """
        if move not in self.generate_legal_moves():
            # Special case: if it's a pawn capturing the king
            captured = self.piece_at(move.to_square)
            from_piece = self.piece_at(move.from_square)
            if captured and captured.piece_type == chess.KING and from_piece and from_piece.piece_type == chess.PAWN:
                return True
            return False

        # If it's a king capture, allow
        captured_piece = self.piece_at(move.to_square)
        if captured_piece and captured_piece.piece_type == chess.KING:
            return True

        # Check drawback blocking
        active_drawback = self.get_active_drawback(self.turn)
        if active_drawback:
            info = get_drawback_info(active_drawback)
            if info and "illegal_moves" in info:
                if info["illegal_moves"](self, self.turn, move):
                    return False
        return True

    def _force_pawn_king_captures(self):
        """
        Adds "pawn capturing a king" moves that might not appear in pseudo-legal moves.
        For example, a forward capture if the king is directly in front of the pawn.
        """
        forced = []
        color = self.turn
        direction = 8 if color == chess.WHITE else -8

        pawns = self.pawns & self.occupied_co[color]
        for pawn_sq in chess.scan_forward(pawns):
            # Check forward
            fwd_sq = pawn_sq + direction
            if 0 <= fwd_sq < 64:
                piece_in_front = self.piece_at(fwd_sq)
                if piece_in_front and piece_in_front.piece_type == chess.KING and piece_in_front.color != color:
                    forced.append(chess.Move(pawn_sq, fwd_sq))

            # Check diagonals
            diag_left = pawn_sq + direction - 1
            if 0 <= diag_left < 64:
                piece_dl = self.piece_at(diag_left)
                if piece_dl and piece_dl.piece_type == chess.KING and piece_dl.color != color:
                    forced.append(chess.Move(pawn_sq, diag_left))

            diag_right = pawn_sq + direction + 1
            if 0 <= diag_right < 64:
                piece_dr = self.piece_at(diag_right)
                if piece_dr and piece_dr.piece_type == chess.KING and piece_dr.color != color:
                    forced.append(chess.Move(pawn_sq, diag_right))

        return forced

    def copy(self):
        """
        Creates a deep copy of the board, preserving drawbacks.
        """
        new_board = DrawbackBoard(fen=self.fen())
        new_board.drawbacks = self.drawbacks.copy()
        return new_board

        return new_board
