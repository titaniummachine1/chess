# movegen.py

from bitboard import Bitboard as bitboard
from GameState.constants import Color, Piece
import tables  # Lookup tables for piece movement

# ------------------------------------------------------------------
# 1) Slide in direction
# ------------------------------------------------------------------
def slide_in_direction(start_square, row_inc, col_inc, board):
    moves_bb = 0
    my_occ_bits = board.combined_color[board.current_turn]
    all_occ_bits = board.combined_all

    row = start_square // 8
    col = start_square % 8

    while True:
        row += row_inc
        col += col_inc
        if not (0 <= row < 8 and 0 <= col < 8):
            break
        sq = row * 8 + col

        if (all_occ_bits >> sq) & 1:
            # Occupied
            if not ((my_occ_bits >> sq) & 1):
                moves_bb |= (1 << sq)  # can capture the opponent
            break
        else:
            moves_bb |= (1 << sq)
    return moves_bb

# ------------------------------------------------------------------
# 2) Sliding pieces
# ------------------------------------------------------------------
def get_bishop_moves_bb(square, board):
    directions = [(1,1), (1,-1), (-1,1), (-1,-1)]
    moves = 0
    for dr, dc in directions:
        moves |= slide_in_direction(square, dr, dc, board)
    return moves & ~board.combined_color[board.current_turn]

def get_rook_moves_bb(square, board):
    directions = [(1,0), (-1,0), (0,1), (0,-1)]
    moves = 0
    for dr, dc in directions:
        moves |= slide_in_direction(square, dr, dc, board)
    return moves & ~board.combined_color[board.current_turn]

def get_queen_moves_bb(square, board):
    directions = [(1,0), (-1,0), (0,1), (0,-1),
                  (1,1), (1,-1), (-1,1), (-1,-1)]
    moves = 0
    for dr, dc in directions:
        moves |= slide_in_direction(square, dr, dc, board)
    return moves & ~board.combined_color[board.current_turn]

# ------------------------------------------------------------------
# 3) Knight, King, Pawn base moves
# ------------------------------------------------------------------
def get_knight_moves_bb(square, board):
    return tables.KNIGHT_MOVES[square] & ~board.combined_color[board.current_turn]

def get_king_moves_bb(square, board):
    """
    Generates king moves using precomputed lookup, plus
    potential castling squares if castling rights are still present.
    """
    color = board.current_turn
    moves = tables.KING_MOVES[square] & ~board.combined_color[color]

    # -- CASTLING LOGIC (simple version) --
    # We'll check if the king is on its starting square, if there's space,
    # and if the relevant castling_right is True. We do NOT check check/attacks.
    # That is left to 'generate_legal_moves' + 'leaves_in_check'.

    # White
    if color == Color.WHITE and square == 4:  # e1
        # kingside: check squares f1,g1 => 5,6
        if board.castling_rights['K']:
            if not bitboard.get_bit(board.combined_all, 5) and \
               not bitboard.get_bit(board.combined_all, 6):
                # add g1 (6) to moves
                moves |= (1 << 6)
        # queenside: check squares d1,c1,b1 => 3,2,1
        if board.castling_rights['Q']:
            if not bitboard.get_bit(board.combined_all, 3) and \
               not bitboard.get_bit(board.combined_all, 2) and \
               not bitboard.get_bit(board.combined_all, 1):
                # add c1 (2) to moves
                moves |= (1 << 2)

    # Black
    if color == Color.BLACK and square == 60: # e8
        # kingside: check squares f8,g8 => 61,62
        if board.castling_rights['k']:
            if not bitboard.get_bit(board.combined_all, 61) and \
               not bitboard.get_bit(board.combined_all, 62):
                moves |= (1 << 62)
        # queenside: check squares d8,c8,b8 => 59,58,57
        if board.castling_rights['q']:
            if not bitboard.get_bit(board.combined_all, 59) and \
               not bitboard.get_bit(board.combined_all, 58) and \
               not bitboard.get_bit(board.combined_all, 57):
                moves |= (1 << 58)

    return moves


def get_pawn_moves_bb(square, board):
    color = board.current_turn

    attacks = tables.PAWN_ATTACKS[color][square]
    attacks &= board.combined_color[~color]  # only if opponent occupies it

    quiets = 0
    if color == Color.WHITE:
        forward1 = square + 8
        if forward1 < 64 and not bitboard.get_bit(board.combined_all, forward1):
            quiets |= bitboard.set_bit(0, forward1)
            if (square // 8) == 1:
                forward2 = square + 16
                if forward2 < 64 and not bitboard.get_bit(board.combined_all, forward2):
                    quiets |= bitboard.set_bit(0, forward2)
    else:
        forward1 = square - 8
        if forward1 >= 0 and not bitboard.get_bit(board.combined_all, forward1):
            quiets |= bitboard.set_bit(0, forward1)
            if (square // 8) == 6:
                forward2 = square - 16
                if forward2 >= 0 and not bitboard.get_bit(board.combined_all, forward2):
                    quiets |= bitboard.set_bit(0, forward2)

    enp_captures = 0
    ep_sq = board.en_passant_sq
    if ep_sq != -1:
        # White
        if color == Color.WHITE:
            # left diag
            if (square + 7) == ep_sq and (square % 8) != 0:
                enp_captures |= bitboard.set_bit(0, ep_sq)
            # right diag
            if (square + 9) == ep_sq and (square % 8) != 7:
                enp_captures |= bitboard.set_bit(0, ep_sq)
        else:
            # Black
            if (square - 7) == ep_sq and (square % 8) != 7:
                enp_captures |= bitboard.set_bit(0, ep_sq)
            if (square - 9) == ep_sq and (square % 8) != 0:
                enp_captures |= bitboard.set_bit(0, ep_sq)

    return (attacks | quiets | enp_captures)


# ------------------------------------------------------------------
# 4) Summon piece-specific generation, then yield moves
# ------------------------------------------------------------------
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
    """Generates all pseudo-legal moves for the current player."""
    from GameState.constants import Piece  # or import globally
    for p in Piece:
        piece_bb = board.get_piece_bb(p, board.current_turn)
        while piece_bb:
            src = bitboard.lsb(piece_bb)
            piece_bb = bitboard.clear_bit(piece_bb, src)

            moves_bb = generate_piece_moves(src, p, board)
            while moves_bb:
                dest = bitboard.lsb(moves_bb)
                moves_bb = bitboard.clear_bit(moves_bb, dest)
                yield (src, dest, None)  # no promotion piece info here by default


# Simple check if a color's king is attacked
def is_king_in_check(board, color):
    from GameState.constants import Piece
    king_bb = board.pieces[color][Piece.KING]
    if king_bb == 0:
        return True  # should never happen, but be safe

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
    # Bishop or Queen
    if get_bishop_moves_bb(king_sq, board) & (board.pieces[opp_color][Piece.BISHOP] | board.pieces[opp_color][Piece.QUEEN]):
        return True
    # Rook or Queen
    if get_rook_moves_bb(king_sq, board) & (board.pieces[opp_color][Piece.ROOK] | board.pieces[opp_color][Piece.QUEEN]):
        return True

    return False

def leaves_in_check(board, move):
    """Test the move in-place: make_move, check, then undo_move."""
    (start_sq, end_sq, promo) = move
    color_moving = board.current_turn

    success = board.make_move(start_sq, end_sq, promo)
    if not success:
        # If we fail to make the move (e.g. no piece on start), treat it as if it's illegal
        return True

    check_status = is_king_in_check(board, color_moving)
    board.undo_move()
    return check_status


def generate_legal_moves(board):
    return filter(lambda mv: not leaves_in_check(board, mv), generate_moves(board))