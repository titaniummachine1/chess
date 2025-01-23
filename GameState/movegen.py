import chess
from GameState.drawback_manager import get_drawback_info

class DrawbackBoard(chess.Board):
    """
    Custom board class for Drawback Chess.
    - Standard rules apply first.
    - Then, drawback-specific restrictions modify legal moves.
    """

    def __init__(self, fen=None, chess960=False):
        super().__init__(fen, chess960=chess960)
        self.drawbacks = {chess.WHITE: None, chess.BLACK: None}  # Store each player's drawback

    def reset(self):
        """Resets the board and reassigns drawbacks."""
        super().reset()  # Reset the board using chess.Board's reset method
        self.drawbacks = {chess.WHITE: None, chess.BLACK: None}  # Clear drawbacks

    def set_drawback(self, color, drawback_name):
        """Assigns a drawback to a player."""
        self.drawbacks[color] = drawback_name

    def get_active_drawback(self, color):
        """Returns the active drawback for a given player."""
        return self.drawbacks.get(color, None)

    def is_variant_end(self):
        """
        Checks if the game is over:
        - A player loses immediately if their king is missing at the start of their turn.
        - Drawback loss conditions are also checked.
        """
        white_king_alive = bool(self.kings & self.occupied_co[chess.WHITE])
        black_king_alive = bool(self.kings & self.occupied_co[chess.BLACK])

        # If it's White's turn but White has no king, White loses (Black wins)
        if self.turn == chess.WHITE and not white_king_alive:
            return True  # White lost
        # If it's Black's turn but Black has no king, Black loses (White wins)
        if self.turn == chess.BLACK and not black_king_alive:
            return True  # Black lost

        # Check if the current player's drawback causes an instant loss
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
        Determines if the current player wins:
        - The game is over, and the opponent's king is missing at the end of the previous move.
        """
        white_king_alive = bool(self.kings & self.occupied_co[chess.WHITE])
        black_king_alive = bool(self.kings & self.occupied_co[chess.BLACK])

        # If it's White's turn but Black's king is missing, White wins
        if self.turn == chess.WHITE and not black_king_alive:
            return True
        # If it's Black's turn but White's king is missing, Black wins
        if self.turn == chess.BLACK and not white_king_alive:
            return True

        return False  # No winner yet

    def is_variant_loss(self):
        """A player loses if their king is missing at the start of their turn."""
        return self.is_variant_end() and not self.is_variant_win()

    def generate_legal_moves(self, from_mask=chess.BB_ALL, to_mask=chess.BB_ALL):
        """
        Generates legal moves considering:
        - Standard rules (moving into check allowed, capturing king allowed)
        - Drawback-specific restrictions (some moves may be illegal)
        """
        # If the game is over, return no moves
        if self.is_variant_end():
            return iter([])

        # Generate all legal moves normally
        legal_moves = list(super().generate_legal_moves(from_mask, to_mask))

        # Apply drawback-based move filtering
        active_drawback = self.get_active_drawback(self.turn)
        if active_drawback:
            drawback_info = get_drawback_info(active_drawback)
            if drawback_info and "illegal_moves" in drawback_info:
                legal_moves = [m for m in legal_moves if not drawback_info["illegal_moves"](self, self.turn, m)]

        return iter(legal_moves)

    def is_legal(self, move):
        """
        Determines if a move is legal:
        - King captures are allowed.
        - Moving into check is allowed (no forced resolution).
        - Drawback-specific move restrictions still apply.
        """
        if move not in self.generate_pseudo_legal_moves():
            return False  # Must be a valid chess move

        # Allow capturing the king (normally illegal in standard chess)
        if self.piece_at(move.to_square) and self.piece_at(move.to_square).piece_type == chess.KING:
            return True  # Capturing a king is legal

        # Apply drawback restrictions
        active_drawback = self.get_active_drawback(self.turn)
        if active_drawback:
            drawback_info = get_drawback_info(active_drawback)
            if drawback_info and "illegal_moves" in drawback_info:
                if drawback_info["illegal_moves"](self, self.turn, move):
                    return False

        return True
