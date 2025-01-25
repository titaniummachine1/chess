import pygame as p
import os
import chess
from GameState.movegen import DrawbackBoard  # Your custom board

IMAGES = {}
SQ_SIZE = 680 // 8  # Chessboard square size

def load_images():
    """
    Load chess piece images into IMAGES dict, e.g. IMAGES['wP'].
    """
    global IMAGES
    pieces = ['wP', 'wR', 'wN', 'wB', 'wQ', 'wK', 'bP', 'bR', 'bN', 'bB', 'bQ', 'bK']
    for piece_key in pieces:
        img_path = os.path.join('images', f'{piece_key}.png')

        # Debug: Check if image path exists
        if not os.path.exists(img_path):
            print(f"Warning: Missing image {img_path}")
            continue

        image_surf = p.image.load(img_path)
        IMAGES[piece_key] = p.transform.smoothscale(image_surf, (SQ_SIZE, SQ_SIZE))

    print(f"Loaded images: {list(IMAGES.keys())}")

def draw_board(screen, dimension=8, width=680, height=680):
    """Draw an 8x8 chessboard (alternating squares)."""
    sq_size = height // dimension
    white = p.Color('#EBEBD0')
    dark = p.Color('#769455')

    for row in range(dimension):
        for col in range(dimension):
            color = white if (row + col) % 2 == 0 else dark
            p.draw.rect(screen, color, p.Rect(col * sq_size, row * sq_size, sq_size, sq_size))

def draw_pieces(screen, board_obj, flipped=False, dimension=8):
    """
    Render the pieces from a DrawbackBoard on the squares.
    """
    sq_size = 680 // dimension
    for sq in chess.SQUARES:
        piece = board_obj.piece_at(sq)
        if piece:
            row = sq // 8
            col = sq % 8
            if flipped:
                draw_row = 7 - row
                draw_col = 7 - col
            else:
                draw_row = row
                draw_col = col

            color_char = 'w' if piece.color == chess.WHITE else 'b'
            piece_type = piece.symbol().upper()
            image_key = color_char + piece_type

            if image_key not in IMAGES:
                print(f"Warning: Missing image for {image_key}")
                continue

            screen.blit(IMAGES[image_key], p.Rect(draw_col * sq_size, draw_row * sq_size, sq_size, sq_size))

def apply_legal_move(board_obj, move, selected_square):
    """
    Handles move execution and piece selection:
      1) If clicking the same square, deselect.
      2) If clicking a new piece of the same color, switch selection.
      3) Otherwise, check if the move is legal via the custom is_legal().
         If so, execute it. If not, keep the selection.
    """
    (start_row, start_col), (end_row, end_col) = move
    start_sq = start_row * 8 + start_col
    end_sq = end_row * 8 + end_col

    # 1) If clicking the same piece, deselect it
    if (start_row, start_col) == (end_row, end_col):
        return None  # Deselect

    # 2) If clicking a new piece of the same color, switch selection
    piece_at_dest = board_obj.piece_at(end_sq)
    if piece_at_dest and board_obj.color_at(end_sq) == board_obj.turn:
        return (end_row, end_col)  # Switch selection to that new piece

    # 3) Otherwise, check custom is_legal() for final authority
    candidate = chess.Move(start_sq, end_sq)
    if board_obj.is_legal(candidate):
        board_obj.push(candidate)
        return None  # Move done, deselect piece
    else:
        print(f"Illegal move: {candidate} (from {start_sq} to {end_sq})")
        return selected_square  # Keep the previous selection if move was illegal

def draw_highlights(screen, board_obj, selected_square, flipped=False):
    """
    Highlight the selected square and possible moves using board_obj.generate_legal_moves().
    """
    if selected_square is None:
        return

    row, col = selected_square
    sq_size = 680 // 8

    disp_row = 7 - row if flipped else row
    disp_col = 7 - col if flipped else col

    highlight_surf = p.Surface((sq_size, sq_size), p.SRCALPHA)
    highlight_surf.fill((255, 255, 0, 100))
    screen.blit(highlight_surf, (disp_col * sq_size, disp_row * sq_size))

    start_sq = row * 8 + col

    # Instead of board_obj.legal_moves, call generate_legal_moves().
    all_legal_moves = list(board_obj.generate_legal_moves())
    valid_dest_squares = [mv.to_square for mv in all_legal_moves if mv.from_square == start_sq]

    for dest_sq in valid_dest_squares:
        end_row = dest_sq // 8
        end_col = dest_sq % 8
        drow = 7 - end_row if flipped else end_row
        dcol = 7 - end_col if flipped else end_col

        move_candidate = chess.Move(start_sq, dest_sq)     
        
        # Check if this move is still legal after drawback filtering
        if move_candidate not in board_obj.legal_moves:
            continue  # Skip if the move isn't actually legal

        is_capture = board_obj.is_capture(move_candidate)

        if is_capture:
            ring_surface = p.Surface((sq_size, sq_size), p.SRCALPHA)
            p.draw.circle(ring_surface, (0, 0, 0, 120), (sq_size // 2, sq_size // 2), sq_size // 2, 7)
            screen.blit(ring_surface, (dcol * sq_size, drow * sq_size))
        else:
            circle_surface = p.Surface((sq_size, sq_size), p.SRCALPHA)
            p.draw.circle(circle_surface, (0, 0, 0, 120), (sq_size // 2, sq_size // 2), sq_size // 7)
            screen.blit(circle_surface, (dcol * sq_size, drow * sq_size))
