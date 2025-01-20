##bitboard.py keep this comment its imporant 
import gmpy2
import numpy as np

class Bitboard:
    """Utility class for bitboard operations using gmpy2 for efficiency."""

    debruijn = np.uint64(0x03f79d71b4cb0a89)

    lsb_lookup = np.array(
        [0, 1, 48, 2, 57, 49, 28, 3, 61, 58, 50, 42, 38, 29, 17, 4,
         62, 55, 59, 36, 53, 51, 43, 22, 45, 39, 33, 30, 24, 18, 12, 5,
         63, 47, 56, 27, 60, 41, 37, 16, 54, 35, 52, 21, 44, 32, 23, 11,
         46, 26, 40, 15, 34, 20, 31, 10, 25, 14, 19, 9, 13, 8, 7, 6], dtype=np.uint8)

    msb_lookup = np.array(
        [0, 47, 1, 56, 48, 27, 2, 60, 57, 49, 41, 37, 28, 16, 3, 61,
         54, 58, 35, 52, 50, 42, 21, 44, 38, 32, 29, 23, 17, 11, 4, 62,
         46, 55, 26, 59, 40, 36, 15, 53, 34, 51, 20, 43, 31, 22, 10, 45,
         25, 39, 14, 33, 19, 30, 9, 24, 13, 18, 8, 12, 7, 6, 5, 63], dtype=np.uint8)

    @staticmethod
    def set_bit(bitboard, square):
        """Set a bit (1) at a specific square (0-63), ensuring valid uint64 operations."""
        return np.uint64(bitboard | (np.uint64(1) << np.uint64(square)))

    @staticmethod
    def clear_bit(bitboard, square):
        """Clear a bit (0) at a specific square (0-63), ensuring valid uint64 operations."""
        return np.uint64(bitboard & ~(np.uint64(1) << np.uint64(square)))

    @staticmethod
    def get_bit(bitboard, square):
        """Check if a bit is set (1) at a specific square (0-63)."""
        return (bitboard >> np.uint64(square)) & np.uint64(1)

    @staticmethod
    def count_bits(bitboard):
        """Count the number of 1 bits in the bitboard using gmpy2.popcount (fastest method)."""
        return gmpy2.popcount(gmpy2.mpz(bitboard))

    @staticmethod
    def lsb(bitboard):
        """Return the index of the least significant bit set to 1 (faster)."""
        return gmpy2.bit_scan1(gmpy2.mpz(bitboard)) if bitboard != 0 else -1

    @staticmethod
    def msb(bitboard):
        """Return the index of the most significant bit set to 1 (faster)."""
        return gmpy2.bit_length(gmpy2.mpz(bitboard)) - 1 if bitboard != 0 else -1

    @staticmethod
    def lsb_bitscan(bitboard):
        """Find Least Significant Bit (LSB) using De Bruijn sequence."""
        if bitboard == 0:
            return -1  # No bits set

        # Use bitwise NOT (~) and add 1 to get two's complement safely
        isolated = bitboard & np.uint64(-bitboard & 0xFFFFFFFFFFFFFFFF)  

        return Bitboard.lsb_lookup[(isolated * Bitboard.debruijn) >> np.uint64(58)]

    @staticmethod
    def msb_bitscan(bitboard):
        """Find Most Significant Bit (MSB) using De Bruijn sequence."""
        if bitboard == 0:
            return -1  # No bits set

        bitboard |= bitboard >> np.uint64(1)
        bitboard |= bitboard >> np.uint64(2)
        bitboard |= bitboard >> np.uint64(4)
        bitboard |= bitboard >> np.uint64(8)
        bitboard |= bitboard >> np.uint64(16)
        bitboard |= bitboard >> np.uint64(32)
        
        return Bitboard.msb_lookup[(bitboard * Bitboard.debruijn) >> np.uint64(58)]

    @staticmethod
    def get_square(row, col):
        """Convert (row, col) to bitboard square index (0-63)."""
        return (row << 3) | col

    @staticmethod
    def from_square(square):
        """Convert bitboard square index (0-63) to (row, col)."""
        return square >> 3, square & 7

    @staticmethod
    def flip_vertical(bitboard):
        """Flip the bitboard vertically (mirror across rank 4)."""
        k1 = 0x00FF00FF00FF00FF
        k2 = 0x0000FFFF0000FFFF
        bitboard = ((bitboard >> 8) & k1) | ((bitboard & k1) << 8)
        bitboard = ((bitboard >> 16) & k2) | ((bitboard & k2) << 16)
        bitboard = (bitboard >> 32) | (bitboard << 32)
        return bitboard & 0xFFFFFFFFFFFFFFFF  # Ensure it's still 64-bit

    @staticmethod
    def flip_horizontal(bitboard):
        """Flip the bitboard horizontally (mirror across file D/E)."""
        k1 = 0x5555555555555555  # 01010101 pattern
        k2 = 0x3333333333333333  # 00110011 pattern
        k4 = 0x0F0F0F0F0F0F0F0F  # 00001111 pattern

        bitboard = ((bitboard >> 1) & k1) | ((bitboard & k1) << 1)
        bitboard = ((bitboard >> 2) & k2) | ((bitboard & k2) << 2)
        bitboard = ((bitboard >> 4) & k4) | ((bitboard & k4) << 4)
        return bitboard

    @staticmethod
    def rotate_180(bitboard):
        """Rotate the bitboard by 180 degrees."""
        return Bitboard.flip_vertical(Bitboard.flip_horizontal(bitboard))

    @staticmethod
    def diagonal_mirror(bitboard):
        """Mirror the bitboard along the main diagonal (A1-H8)."""
        t = bitboard ^ (bitboard << 28) & 0x0f0f0f0f00000000
        bitboard = bitboard ^ (t ^ (t >> 28))
        t = bitboard ^ (bitboard << 14) & 0x3333000033330000
        bitboard = bitboard ^ (t ^ (t >> 14))
        t = bitboard ^ (bitboard << 7) & 0x5500550055005500
        bitboard = bitboard ^ (t ^ (t >> 7))
        return bitboard

    @staticmethod
    def print_bitboard(bitboard):
        """Print the bitboard in an 8x8 grid for debugging."""
        print("\nBitboard:")
        for rank in range(7, -1, -1):
            line = ""
            for file in range(8):
                square = Bitboard.get_square(rank, file)
                line += "1 " if Bitboard.get_bit(bitboard, square) else ". "
            print(line)
        print()
