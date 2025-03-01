import chess
from AI.zobrist import compute_zobrist_key

class IncrementalBoard(chess.Board):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.zobrist_key = compute_zobrist_key(self)
    
    def push(self, move):
        ret = super().push(move)
        # Update the cached Zobrist key after a move.
        self.zobrist_key = compute_zobrist_key(self)
        return ret
    
    def pop(self):
        ret = super().pop()
        # Update the cached Zobrist key after undoing a move.
        self.zobrist_key = compute_zobrist_key(self)
        return ret
