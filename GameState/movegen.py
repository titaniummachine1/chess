import chess
from GameState.drawback_manager import check_drawback, check_drawback_loss

class DrawbackBoard(chess.Board):
    def __init__(self):
        super().__init__()
        self.drawbacks = {chess.WHITE: None, chess.BLACK: None}  # Each player gets a drawback

    def set_drawback(self, color, drawback_name):
        """Assign a drawback to a player."""
        self.drawbacks[color] = drawback_name

    def get_drawback(self, color):
        """Retrieve the current drawback of a player."""
        return self.drawbacks[color]

    def is_variant_end(self):
        """Game ends when:
        - A king is captured.
        - A drawback forces a player to lose.
        """
        if not self.kings & self.occupied_co[chess.WHITE] or not self.kings & self.occupied_co[chess.BLACK]:
            return True  # King captured

        return check_drawback_loss(self)  # Drawback condition met

    def is_variant_win(self):
        """A player wins if:
        - Their opponent’s king is missing.
        - The opponent loses due to a drawback condition.
        """
        if not self.kings & self.occupied_co[not self.turn]:
            return True  # Opponent's king is gone

        return check_drawback_loss(self) and not check_drawback_loss(self, self.turn)

    def generate_legal_moves(self, from_mask=chess.BB_ALL, to_mask=chess.BB_ALL):
        """Override move generation:
        - ✅ Allows moving into check
        - ✅ Allows capturing kings
        - ✅ Applies drawback restrictions
        """
        drawback = self.get_drawback(self.turn)  # Get the current drawback

        for move in super().generate_pseudo_legal_moves(from_mask, to_mask):
            if check_drawback(self, move, drawback):  # Check if move is valid under the drawback
                yield move

    def is_legal(self, move):
        """Override legality check:
        - Allows moving into check
        - Allows capturing kings
        """
        return move in self.generate_legal_moves()