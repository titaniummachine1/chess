import chess
from drawback_manager import get_drawback_info

class DrawbackBoard(chess.Board):
    def __init__(self):
        super().__init__()
        self.drawbacks = {chess.WHITE: None, chess.BLACK: None}  # Stores current drawbacks

    def set_drawback(self, color, drawback_name):
        """Assign a drawback to a player."""
        self.drawbacks[color] = drawback_name

    def get_drawback(self, color):
        """Retrieve the player's current drawback."""
        return self.drawbacks[color]

    def is_variant_end(self):
        """Check for end conditions: capturing the king or losing due to drawback."""
        if not self.kings & self.occupied_co[chess.WHITE] or not self.kings & self.occupied_co[chess.BLACK]:
            return True  # King captured

        return self.check_drawback_loss(chess.WHITE) or self.check_drawback_loss(chess.BLACK)

    def is_variant_win(self):
        """A player wins if the opponent's king is gone or they lose to a drawback."""
        if not self.kings & self.occupied_co[not self.turn]:
            return True

        return self.check_drawback_loss(not self.turn) and not self.check_drawback_loss(self.turn)

    def check_drawback_loss(self, color):
        """Check if a player's drawback forces them to lose."""
        drawback = self.get_drawback(color)
        if drawback:
            drawback_info = get_drawback_info(drawback)
            if drawback_info.get("loss_condition"):
                return drawback_info["loss_condition"](self, color)
        return False

    def generate_legal_moves(self, from_mask=chess.BB_ALL, to_mask=chess.BB_ALL):
        """Modify move generation based on drawbacks."""
        drawback = self.get_drawback(self.turn)
        drawback_info = get_drawback_info(drawback)

        for move in super().generate_pseudo_legal_moves(from_mask, to_mask):
            if not drawback or drawback_info["legal_moves"](self, move):
                yield move

    def is_legal(self, move):
        """Override legality check to allow moving into check and capturing kings."""
        return move in self.generate_legal_moves()
