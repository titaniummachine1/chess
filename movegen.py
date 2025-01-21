# movegen.py

from bitboard import Bitboard as bitboard
from GameState.constants import Color, Piece
import tables  # or your lookup tables for knight, king, pawn attacks

#------------------------------------------------------------------
# 1) Sliding
#------------------------------------------------------------------
def slide_in_direction(start_sq, row_inc, col_inc, board):
    """
    Return a bitboard of squares reachable by continuing row_inc/col_inc
    until blocked or out of board.
    """
    moves_bb = 0
    my_occ = board.combined_color[board.current_turn]
    all_occ = board.combined_all

    row = start_sq // 8
    col = start_sq % 8

    while True:
        row += row_inc
        col += col_inc
        if row < 0 or row > 7 or col < 0 or col > 7:
            break

        sq = row * 8 + col
        if (all_occ >> sq) & 1:
            # Occupied
            if not ((my_occ >> sq) & 1):
                moves_bb |= (1 << sq)  # capture
            break
        else:
            moves_bb |= (1 << sq)

    return moves_bb


def get_bishop_moves_bb(square, board):
    directions = [(1,1), (1,-1), (-1,1), (-1,-1)]
    res = 0
    for dr, dc in directions:
        res |= slide_in_direction(square, dr, dc, board)
    return res & ~board.combined_color[board.current_turn]

def get_rook_moves_bb(square, board):
    directions = [(1,0), (-1,0), (0,1), (0,-1)]
    res = 0
    for dr, dc in directions:
        res |= slide_in_direction(square, dr, dc, board)
    return res & ~board.combined_color[board.current_turn]

def get_queen_moves_bb(square, board):
    directions = [(1,0), (-1,0), (0,1), (0,-1),
                  (1,1), (1,-1), (-1,1), (-1,-1)]
    res = 0
    for dr, dc in directions:
        res |= slide_in_direction(square, dr, dc, board)
    return res & ~board.combined_color[board.current_turn]

#------------------------------------------------------------------
# 2) Knight, King, Pawn
#------------------------------------------------------------------
def get_knight_moves_bb(square, board):
    # Use precomputed or do bit shifts
    return tables.KNIGHT_MOVES[square] & ~board.combined_color[board.current_turn]

def get_king_moves_bb(square, board):
    color = board.current_turn
    moves = tables.KING_MOVES[square] & ~board.combined_color[color]
    all_occ = board.combined_all

    # Minimal castling addition:
    # White king at e1=4
    if color == Color.WHITE and square == 4:
        # kingside => squares f1=5, g1=6
        if board.castling_rights['K']:
            # check if f1,g1 empty
            if not bitboard.get_bit(all_occ, 5) and not bitboard.get_bit(all_occ, 6):
                moves |= (1 << 6)
        # queenside => squares d1=3, c1=2, b1=1
        if board.castling_rights['Q']:
            if not bitboard.get_bit(all_occ, 3) and \
               not bitboard.get_bit(all_occ, 2) and \
               not bitboard.get_bit(all_occ, 1):
                moves |= (1 << 2)
    # Black king at e8=60
    if color == Color.BLACK and square == 60:
        # kingside => f8=61, g8=62
        if board.castling_rights['k']:
            if not bitboard.get_bit(all_occ, 61) and not bitboard.get_bit(all_occ, 62):
                moves |= (1 << 62)
        # queenside => d8=59, c8=58, b8=57
        if board.castling_rights['q']:
            if not bitboard.get_bit(all_occ, 59) and \
               not bitboard.get_bit(all_occ, 58) and \
               not bitboard.get_bit(all_occ, 57):
                moves |= (1 << 58)

    return moves

def get_pawn_moves_bb(square, board):
    color = board.current_turn
    all_occ = board.combined_all
    opp_occ = board.combined_color[~color]

    # Pawn captures from tables, but only if an opponent is actually there
    attacks = tables.PAWN_ATTACKS[color][square] & opp_occ

    quiets = 0
    if color == Color.WHITE:
        forward1 = square + 8
        if forward1 < 64 and not bitboard.get_bit(all_occ, forward1):
            quiets |= (1 << forward1)
            if (square // 8) == 1:  # white second rank
                forward2 = square + 16
                if forward2 < 64 and not bitboard.get_bit(all_occ, forward2):
                    quiets |= (1 << forward2)
    else:
        forward1 = square - 8
        if forward1 >= 0 and not bitboard.get_bit(all_occ, forward1):
            quiets |= (1 << forward1)
            if (square // 8) == 6:  # black second rank from top
                forward2 = square - 16
                if forward2 >= 0 and not bitboard.get_bit(all_occ, forward2):
                    quiets |= (1 << forward2)

    # En Passant
    enp_captures = 0
    ep_sq = board.en_passant_sq
    if ep_sq != -1:
        # White
        if color == Color.WHITE:
            if (square + 7) == ep_sq and (square % 8) != 0:
                enp_captures |= (1 << ep_sq)
            if (square + 9) == ep_sq and (square % 8) != 7:
                enp_captures |= (1 << ep_sq)
        else:
            if (square - 7) == ep_sq and (square % 8) != 7:
                enp_captures |= (1 << ep_sq)
            if (square - 9) == ep_sq and (square % 8) != 0:
                enp_captures |= (1 << ep_sq)

    return (attacks | quiets | enp_captures)

#------------------------------------------------------------------
# 3) Summon piece-specific generation
#------------------------------------------------------------------
def generate_piece_moves(square, piece, board):
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
    from GameState.constants import Piece
    color = board.current_turn
    for ptype in Piece:
        bb = board.get_piece_bb(ptype, color)
        while bb:
            src = bitboard.lsb(bb)
            bb = bitboard.clear_bit(bb, src)
            moves_bb = generate_piece_moves(src, ptype, board)
            while moves_bb:
                dst = bitboard.lsb(moves_bb)
                moves_bb = bitboard.clear_bit(moves_bb, dst)
                yield (src, dst, None)  # no promotion piece by default

#------------------------------------------------------------------
# 4) Checking if in check
#------------------------------------------------------------------
def is_king_in_check(board, color):
    from GameState.constants import Piece
    king_bb = board.pieces[color][Piece.KING]
    if king_bb == 0:
        return True  # No king found?? let's say it's "in check"

    king_sq = bitboard.lsb(king_bb)
    opp_color = ~color

    # Pawn
    if tables.PAWN_ATTACKS[color][king_sq] & board.pieces[opp_color][Piece.PAWN]:
        return True
    # Knight
    if tables.KNIGHT_MOVES[king_sq] & board.pieces[opp_color][Piece.KNIGHT]:
        return True
    # King
    if tables.KING_MOVES[king_sq] & board.pieces[opp_color][Piece.KING]:
        return True
    # Diagonals => bishop, queen
    if get_bishop_moves_bb(king_sq, board) & (board.pieces[opp_color][Piece.BISHOP] | board.pieces[opp_color][Piece.QUEEN]):
        return True
    # Lines => rook, queen
    if get_rook_moves_bb(king_sq, board) & (board.pieces[opp_color][Piece.ROOK] | board.pieces[opp_color][Piece.QUEEN]):
        return True
    return False

def leaves_in_check(board, move):
    (start_sq, end_sq, promo) = move
    color = board.current_turn

    success = board.make_move(start_sq, end_sq, promo)
    if not success:
        # e.g. no piece at start
        return True

    in_check = is_king_in_check(board, color)

    board.undo_move()
    return in_check

def generate_legal_moves(board):
    return filter(lambda mv: not leaves_in_check(board, mv),
                  generate_moves(board))
