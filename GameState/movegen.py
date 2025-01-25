# GameState/movegen.py

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
        """Assign a named drawback to a specific player."""
        if color not in [chess.WHITE, chess.BLACK]:
            raise ValueError("Invalid color for drawback assignment.")
        
        self.drawbacks[color] = drawback_name
        print(f"Set drawback for {'White' if color == chess.WHITE else 'Black'}: {drawback_name}")


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
                loss_condition = drawback_info["loss_condition"]
                if callable(loss_condition) and loss_condition(self, self.turn):
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
        The current player loses if:
        - They have no legal moves, or
        - Their own king is missing, or
        - A drawback triggers a loss.
        """
        # Check if the game has ended due to missing kings or drawback-triggered loss
        if self.is_variant_end():
            return not self.is_variant_win()

        # Additionally, if the player has no legal moves, they lose
        if not self._has_any_legal_move():
            print(f"{'White' if self.turn == chess.WHITE else 'Black'} has no legal moves and loses!")
            return True

        return False

    def _has_any_legal_move(self):
        """
        Checks if the current player has any legal moves without invoking generate_legal_moves.
        This prevents recursion by directly accessing pseudo-legal moves and applying drawback filters.
        """
        active_drawback = self.get_active_drawback(self.turn)

        # Iterate through pseudo-legal moves
        for move in super().generate_pseudo_legal_moves():
            # Apply drawbacks
            if active_drawback:
                drawback_info = get_drawback_info(active_drawback)
                if drawback_info and "illegal_moves" in drawback_info:
                    if drawback_info["illegal_moves"](self, self.turn, move):
                        continue  # Move is blocked by drawback

            # Allow pawn capturing a king even if it's normally illegal
            captured_piece = self.piece_at(move.to_square)
            if captured_piece and captured_piece.piece_type == chess.KING and self.piece_at(move.from_square).piece_type == chess.PAWN:
                return True  # Legal move found

            # Any other pseudo-legal move is considered legal
            return True  # Legal move found

        # Additionally, check forced pawn captures
        forced_moves = self._force_pawn_king_captures()
        for move in forced_moves:
            # Apply drawbacks
            if active_drawback:
                drawback_info = get_drawback_info(active_drawback)
                if drawback_info and "illegal_moves" in drawback_info:
                    if drawback_info["illegal_moves"](self, self.turn, move):
                        continue  # Move is blocked by drawback

            # Move is allowed
            return True  # Legal move found

        # No legal moves found
        return False

    def generate_legal_moves(self, from_mask=chess.BB_ALL, to_mask=chess.BB_ALL):
        """Ensure AI and player moves respect drawbacks."""

        if self.is_variant_loss():
            return iter([])

        # Generate base pseudo-legal moves
        moves = list(super().generate_pseudo_legal_moves(from_mask, to_mask))

        # Apply drawback filtering for the current player
        active_drawback = self.get_active_drawback(self.turn)
        if active_drawback:
            drawback_info = get_drawback_info(active_drawback)
            if drawback_info and "illegal_moves" in drawback_info:
                moves = [m for m in moves if not drawback_info["illegal_moves"](self, self.turn, m)]

        return iter(moves)  # Ensure only filtered moves are returned


    def is_legal(self, move):
        """
        Determines if a move is legal:
          - Allows capturing the king,
          - Ignores check rules,
          - Respects any drawback-based restrictions.
        """
        # Must be pseudo-legal or a forced pawn-king capture
        if move not in self.generate_legal_moves():
            # Check if it's a pawn capturing a king
            captured_piece = self.piece_at(move.to_square)
            if captured_piece and captured_piece.piece_type == chess.KING:
                piece = self.piece_at(move.from_square)
                if piece and piece.piece_type == chess.PAWN:
                    # Allow pawn to capture king regardless of standard rules
                    return True
            return False

        # If the move captures a king, it's allowed
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

    def _force_pawn_king_captures(self):
        """
        Force-add any "pawn capturing a king" moves
        that the library would normally consider illegal.
        For example, a forward capture if the king is directly in front of the pawn.
        """
        forced_moves = []

        # Determine movement direction based on color
        color = self.turn
        direction = 8 if color == chess.WHITE else -8  # White moves "up" (towards higher square numbers), Black "down"

        # Identify all pawns of the current player
        pawns = self.pawns & self.occupied_co[color]

        for pawn_sq in chess.scan_forward(pawns):
            # Check the square in front (pawn_sq + direction)
            fwd_sq = pawn_sq + direction
            if 0 <= fwd_sq < 64:
                piece_in_front = self.piece_at(fwd_sq)
                if piece_in_front and piece_in_front.piece_type == chess.KING and piece_in_front.color != color:
                    forced_moves.append(chess.Move(pawn_sq, fwd_sq))

            # Check diagonal left (pawn_sq + direction - 1)
            diag_left = pawn_sq + direction - 1
            if 0 <= diag_left < 64:
                piece_dl = self.piece_at(diag_left)
                if piece_dl and piece_dl.piece_type == chess.KING and piece_dl.color != color:
                    forced_moves.append(chess.Move(pawn_sq, diag_left))

            # Check diagonal right (pawn_sq + direction + 1)
            diag_right = pawn_sq + direction + 1
            if 0 <= diag_right < 64:
                piece_dr = self.piece_at(diag_right)
                if piece_dr and piece_dr.piece_type == chess.KING and piece_dr.color != color:
                    forced_moves.append(chess.Move(pawn_sq, diag_right))

        return forced_moves
    
    def copy(self):
        """Creates a deep copy of the board, preserving drawbacks."""
        new_board = DrawbackBoard(fen=self.fen())
        new_board.drawbacks = self.drawbacks.copy()
        return new_board

