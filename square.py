import numpy as np

from GameState.constants import Rank, File

class Square:
    def __init__(self, index):
        self.index = index

    @classmethod
    def from_position(cls, row, col):
        """Convert (row, col) to square index (0-63)."""
        return cls((row << 3) | col)  # 8 * row + col

    def to_index(self):
        """Return the square index as an integer (0-63)."""
        return self.index

    def to_bitboard(self):
        """Return the bitboard representation of this square."""
        return 1 << self.index
