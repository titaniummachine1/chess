import chess
from GameState.drawback_manager import get_drawback_info

class DrawbackBoard(chess.Board):
    """
    Custom board class for Drawback Chess.
    It applies standard rules, then filters legal moves based on drawbacks.
    """
    
    def __init__(self, fen=None, chess960=False):
        super().__init__(fen, chess960=chess960)
        self.drawbacks = {chess.WHITE: None, chess.BLACK: None}  # Each player's drawback

    def set_drawback(self, color, drawback_name):
        """Assigns a drawback to a player."""
        self.drawbacks[color] = drawback_name

    def get_active_drawback(self, color):
        """Returns the active drawback for a given player."""
        return self.drawbacks.get(color, None)

    def is_variant_end(self):
        """Checks if the game is over (king captured or drawback loss condition)."""
        # Check if a king is missing => game over
        if not any(self.kings & self.occupied_co[chess.WHITE]):
            return True
        if not any(self.kings & self.occupied_co[chess.BLACK]):
            return True
        
        # Check if the current player's drawback causes an instant loss
        active_drawback = self.get_active_drawback(self.turn)
        if active_drawback:
            drawback_info = get_drawback_info(active_drawback)
            if drawback_info and "loss_condition" in drawback_info:
                if drawback_info["loss_condition"](self, self.turn):
                    return True

        return False

    def is_variant_win(self):
        """Checks if the current player wins (only when opponent is in a losing position)."""
        if self.is_variant_end():
            return not self.occupied_co[self.turn]  # If no pieces left, they lose
        return False

    def is_variant_loss(self):
        """Checks if the current player loses."""
        return self.is_variant_end() and not self.is_variant_win()

    def generate_legal_moves(self, from_mask=chess.BB_ALL, to_mask=chess.BB_ALL):
        """
        Generates legal moves considering:
        - Standard variant rules (moving into check allowed, capturing king allowed)
        - Drawback-specific move restrictions
        """
        # If the game is over, stop move generation
        if self.is_variant_end():
            return iter([])

        # Generate all pseudo-legal moves
        moves = list(super().generate_pseudo_legal_moves(from_mask, to_mask))

        # Get active drawback
        active_drawback = self.get_active_drawback(self.turn)
        if active_drawback:
            drawback_info = get_drawback_info(active_drawback)
            if drawback_info and "illegal_moves" in drawback_info:
                moves = [m for m in moves if not drawback_info["illegal_moves"](self, self.turn, m)]

        return iter(moves)

    def is_legal(self, move):
        """
        Determines if a move is legal, considering:
        - Default rules (pseudo-legal moves)
        - Drawback-specific restrictions
        """
        if move not in self.generate_pseudo_legal_moves():
            return False

        # Get active drawback
        active_drawback = self.get_active_drawback(self.turn)
        if active_drawback:
            drawback_info = get_drawback_info(active_drawback)
            if drawback_info and "illegal_moves" in drawback_info:
                if drawback_info["illegal_moves"](self, self.turn, move):
                    return False

        return True
