import chess

class DrawbackBoard(chess.Board):
    def __init__(self):
        super().__init__()
        self.drawbacks = {chess.WHITE: None, chess.BLACK: None}  # Track drawbacks per player

    def set_drawback(self, color, drawback_name):
        """Assign a drawback to a player."""
        self.drawbacks[color] = drawback_name

    def get_drawback(self, color):
        """Retrieve the current drawback of a player."""
        return self.drawbacks[color]

    def is_variant_end(self):
        """Game ends when a king is captured."""
        return not self.kings & self.occupied_co[chess.WHITE] or not self.kings & self.occupied_co[chess.BLACK])

    def is_variant_win(self):
        """A player wins if the opponent's king is missing."""
        return not self.kings & self.occupied_co[not self.turn]

    def generate_legal_moves(self, from_mask=chess.BB_ALL, to_mask=chess.BB_ALL):
        """
        Generate moves **without standard legality rules**.
        Moves are only restricted by drawbacks.
        """
        drawback = self.get_drawback(self.turn)  # Get the player's current drawback

        # Get all possible moves without legality checks
        for move in super().generate_pseudo_legal_moves(from_mask, to_mask):
            if self.is_move_allowed_by_drawback(move, drawback):
                yield move

    def is_move_allowed_by_drawback(self, move, drawback):
        """Check if a move is allowed under the player's current drawback."""
        from drawback_manager import check_drawback  # Import dynamic drawback rules
        return check_drawback(self, move, drawback)

    def is_legal(self, move):
        """
        Overriding legality check:
        - ✅ Allows moving into check
        - ✅ Allows capturing kings
        """
        return move in self.generate_legal_moves()
