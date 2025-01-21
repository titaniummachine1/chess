##movegen.py keep this comment its improtant
import itertools
from bitboard import Bitboard as bitboard
from GameState.constants import Color, Piece
import tables  # Lookup tables for piece movement

# ------------------------------------------------------------------
# 1) A helper function to "slide" along a single direction
#    until we hit the edge or a blocking piece.
# ------------------------------------------------------------------
def slide_in_direction(start_square, row_inc, col_inc, board):
    """
    Return a bitboard of all squares reachable from `start_square`
    by moving (row_inc, col_inc) step by step, stopping if blocked.
    """
    moves_bb = 0

    # Occupancy info
    my_occ_bits = board.combined_color[board.current_turn]
    all_occ_bits = board.combined_all

    row = start_square // 8
    col = start_square % 8

    while True:
        row += row_inc
        col += col_inc
        # Off board check
        if row < 0 or row > 7 or col < 0 or col > 7:
            break

        sq = row * 8 + col

        # If there is any piece on 'sq'
        if (all_occ_bits >> sq) & 1:
            # It's blocked here. If it's the opponent's piece, we can capture.
            if not ((my_occ_bits >> sq) & 1):
                moves_bb |= (1 << sq)
            break
        else:
            # Empty square => we can move there and keep going
            moves_bb |= (1 << sq)

    return moves_bb

# ------------------------------------------------------------------
# 2) Replace the bishop/rook/queen "mask" approach with proper ray scans
# ------------------------------------------------------------------

def get_bishop_moves_bb(square, board):
    """Generate bishop moves by scanning 4 diagonal directions."""
    directions = [(1, 1), (1, -1), (-1, 1), (-1, -1)]
    moves = 0
    for (dr, dc) in directions:
        moves |= slide_in_direction(square, dr, dc, board)
    # Exclude squares occupied by my own color
    return moves & ~board.combined_color[board.current_turn]

def get_rook_moves_bb(square, board):
    """Generate rook moves by scanning 4 orthogonal directions."""
    directions = [(1, 0), (-1, 0), (0, 1), (0, -1)]
    moves = 0
    for (dr, dc) in directions:
        moves |= slide_in_direction(square, dr, dc, board)
    return moves & ~board.combined_color[board.current_turn]

def get_queen_moves_bb(square, board):
    """
    Generate queen moves by combining rook + bishop directions
    (8 directions total).
    """
    directions = [
        (1, 0), (-1, 0), (0, 1), (0, -1),    # rook-like
        (1, 1), (1, -1), (-1, 1), (-1, -1)   # bishop-like
    ]
    moves = 0
    for (dr, dc) in directions:
        moves |= slide_in_direction(square, dr, dc, board)
    return moves & ~board.combined_color[board.current_turn]

# ------------------------------------------------------------------
# 3) Keep the Pawn, Knight, King code from "tables"
# ------------------------------------------------------------------

def get_king_moves_bb(square, board):
    """Generates king moves using precomputed lookup tables."""
    return tables.KING_MOVES[square] & ~board.combined_color[board.current_turn]

def get_knight_moves_bb(square, board):
    """Generates knight moves using precomputed lookup tables."""
    return tables.KNIGHT_MOVES[square] & ~board.combined_color[board.current_turn]

def get_pawn_moves_bb(square, board):
    """Generates pawn moves including attacks, quiet pushes, double pushes, en passant captures."""
    color = board.current_turn

    # 1) Normal Attacks (from precomputed table), but only squares occupied by opponent
    attacks = tables.PAWN_ATTACKS[color][square]
    attacks &= board.combined_color[~color]  # Only valid if an opponent occupies it

    # 2) Single Push
    quiets = 0
    if color == Color.WHITE:
        forward1 = square + 8
        if forward1 < 64 and not bitboard.get_bit(board.combined_all, forward1):
            quiets |= bitboard.set_bit(0, forward1)

            # 3) Double Push (from rank 1 -> rank 3)
            # square's row = square//8. If row == 1 => do double
            if (square // 8) == 1:
                forward2 = square + 16
                if forward2 < 64 and not bitboard.get_bit(board.combined_all, forward2):
                    quiets |= bitboard.set_bit(0, forward2)

    else:
        forward1 = square - 8
        if forward1 >= 0 and not bitboard.get_bit(board.combined_all, forward1):
            quiets |= bitboard.set_bit(0, forward1)

            # Double Push (from rank 6 -> rank 4)
            if (square // 8) == 6:
                forward2 = square - 16
                if forward2 >= 0 and not bitboard.get_bit(board.combined_all, forward2):
                    quiets |= bitboard.set_bit(0, forward2)

    # 4) En Passant captures
    # If board.en_passant_sq != -1, check if that square is diagonally adjacent
    enp_captures = 0
    ep_sq = board.en_passant_sq
    if ep_sq != -1:
        # White pawns: can capture ep_sq if it is exactly (square+7) or (square+9) 
        # but also must match the file constraints
        if color == Color.WHITE:
            # left diagonal
            if (square + 7) == ep_sq and (square % 8) != 0:
                enp_captures |= bitboard.set_bit(0, ep_sq)
            # right diagonal
            if (square + 9) == ep_sq and (square % 8) != 7:
                enp_captures |= bitboard.set_bit(0, ep_sq)
        else:
            # Black pawns
            if (square - 7) == ep_sq and (square % 8) != 7:
                enp_captures |= bitboard.set_bit(0, ep_sq)
            if (square - 9) == ep_sq and (square % 8) != 0:
                enp_captures |= bitboard.set_bit(0, ep_sq)

    return (attacks | quiets | enp_captures)


# ------------------------------------------------------------------
# 4) Summon piece-specific generation, then yield moves
# ------------------------------------------------------------------

def generate_piece_moves(square, piece, board):
    """Generates all pseudo-legal moves for a given piece using bitboards."""
    if piece == Piece.PAWN:
        return get_pawn_moves_bb(square, board)
    elif piece == Piece.KNIGHT:
        return get_knight_moves_bb(square, board)
    elif piece == Piece.BISHOP:
        return get_bishop_moves_bb(square, board)
    elif piece == Piece.ROOK:
        return get_rook_moves_bb(square, board)
    elif piece == Piece.QUEEN:
        return get_queen_moves_bb(square, board)
    elif piece == Piece.KING:
        return get_king_moves_bb(square, board)
    else:
        raise RuntimeError(f"Invalid piece: {piece}")

def generate_moves(board):
    """Generates all pseudo-legal moves for the current player."""
    for piece in Piece:
        piece_bb = board.get_piece_bb(piece, board.current_turn)
        while piece_bb:
            src = bitboard.lsb(piece_bb)          # least significant bit
            piece_bb = bitboard.clear_bit(piece_bb, src)

            moves = generate_piece_moves(src, piece, board)
            while moves:
                dest = bitboard.lsb(moves)
                yield (src, dest, None)           # (startSquare, endSquare, promotionInfo)
                moves = bitboard.clear_bit(moves, dest)

def generate_legal_moves(board):
    """Filters out moves that leave our king in check."""
    return filter(lambda m: not leaves_in_check(board, m), generate_moves(board))

def leaves_in_check(board, move):
    """Check if applying `move` leaves our king in check."""
    new_board = board.apply_move(move)
    new_board.current_turn = ~new_board.current_turn  # Switch perspective

    # Find my king's position
    my_king_sq = bitboard.lsb(new_board.get_piece_bb(Piece.KING, new_board.current_turn))
    opp_color = ~new_board.current_turn

    # Check various attacks
    if tables.PAWN_ATTACKS[new_board.current_turn][my_king_sq] & new_board.get_piece_bb(Piece.PAWN, opp_color):
        return True
    if tables.KNIGHT_MOVES[my_king_sq] & new_board.get_piece_bb(Piece.KNIGHT, opp_color):
        return True
    if tables.KING_MOVES[my_king_sq] & new_board.get_piece_bb(Piece.KING, opp_color):
        return True
    # For bishop/rook attacks, use the same newBoard sliding logic:
    if get_bishop_moves_bb(my_king_sq, new_board) & (new_board.get_piece_bb(Piece.BISHOP, opp_color) |
                                                     new_board.get_piece_bb(Piece.QUEEN, opp_color)):
        return True
    if get_rook_moves_bb(my_king_sq, new_board) & (new_board.get_piece_bb(Piece.ROOK, opp_color) |
                                                   new_board.get_piece_bb(Piece.QUEEN, opp_color)):
        return True

    return False