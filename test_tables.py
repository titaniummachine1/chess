import AI.piece_square_table as pst
import chess

def print_piece_table(piece, color, phase="mg"):
    """Print the piece-square table in board layout format"""
    color_key = "white" if color == chess.WHITE else "black"
    table = pst.piece_square_tables[color_key][phase][piece]
    
    print(f"{color_key.capitalize()} {piece} ({phase}):")
    print("    A    B    C    D    E    F    G    H")
    for rank in range(7, -1, -1):
        rank_values = []
        for file in range(8):
            square = rank * 8 + file
            rank_values.append(f"{table[square]:4d}")
        print(f"{rank+1} {' '.join(rank_values)} {rank+1}")
    print("    A    B    C    D    E    F    G    H")
    print()

# Test knight tables for both colors
print_piece_table("N", chess.WHITE)
print_piece_table("N", chess.BLACK)

# Test pawn tables for both colors
print_piece_table("P", chess.WHITE)
print_piece_table("P", chess.BLACK) 