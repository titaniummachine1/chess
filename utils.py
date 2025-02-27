##utils.py do nto remove this comment you damn idiot

import pygame as p
import os
import chess
from GameState.movegen import DrawbackBoard  # Your custom board

# Global image cache to prevent reloading
PIECES_CACHE = {}
BOARD_HEIGHT = 640  # Default value, will be overridden by main.py

def load_images(square_size):
    """
    Load the chess piece images once, scaled to the square size.
    Uses a cache to avoid reloading images unnecessarily.
    """
    global PIECES_CACHE
    
    # Return cached images if they exist for this square size
    cache_key = f"size_{square_size}"
    if cache_key in PIECES_CACHE:
        return PIECES_CACHE[cache_key]
    
    pieces = ['wP', 'wR', 'wN', 'wB', 'wQ', 'wK', 'bP', 'bR', 'bN', 'bB', 'bQ', 'bK']
    piece_images = {}
    
    try:
        for piece in pieces:
            filename = f"images/{piece}.png"
            img = p.image.load(filename)
            # Scale to square size (with a small margin)
            piece_size = int(square_size * 0.85)  # 85% of square size for margin
            piece_images[piece] = p.transform.scale(img, (piece_size, piece_size))
        print(f"Loaded images: {pieces}")
        
        # Store in cache
        PIECES_CACHE[cache_key] = piece_images
        
    except Exception as e:
        print(f"Error loading images: {e}")
    
    return piece_images

def draw_board(screen, dimension, width, height, flipped=False, offset_y=40, offset_x=0):
    """
    Draw the chess board with coordinates.
    Uses BOARD_HEIGHT for consistent square sizing.
    """
    colors = [p.Color("white"), p.Color("gray")]
    square_size = BOARD_HEIGHT // dimension
    font = p.font.SysFont(None, 20)
    
    # Fill background
    screen.fill(p.Color("black"))
    
    # Draw squares
    for row in range(dimension):
        for col in range(dimension):
            color = colors[(row + col) % 2]
            
            p.draw.rect(
                screen, color, 
                p.Rect(offset_x + col * square_size, offset_y + row * square_size, 
                       square_size, square_size)
            )
    
    # Draw coordinates - files (a-h)
    for col in range(dimension):
        # Adjust column index for flipped board
        file_idx = col if not flipped else 7 - col
        file_label = chr(97 + file_idx)  # ASCII 'a' = 97
        
        # Draw at bottom of board
        label = font.render(file_label, True, p.Color("white"))
        screen.blit(label, (
            offset_x + col * square_size + square_size//2 - label.get_width()//2, 
            offset_y + dimension * square_size + 5
        ))
        
    # Draw coordinates - ranks (1-8)
    for row in range(dimension):
        # Adjust row index for flipped board
        rank_idx = row if flipped else 7 - row
        rank_label = str(rank_idx + 1)
        
        # Draw at left of board
        label = font.render(rank_label, True, p.Color("white"))
        screen.blit(label, (
            offset_x - label.get_width() - 5, 
            offset_y + row * square_size + square_size//2 - label.get_height()//2
        ))

def draw_pieces(screen, board, flipped, dimension, offset_y=40, offset_x=0):
    """
    Draw the chess pieces on the board, using consistent square size calculation.
    Fixes: correctly position pieces on their squares.
    """
    # Use BOARD_HEIGHT for consistent square size across functions
    square_size = BOARD_HEIGHT // dimension
    pieces = load_images(square_size)
    
    # Draw each piece
    for row in range(dimension):
        for col in range(dimension):
            # Convert display coordinates to chess coordinates
            chess_row = row if flipped else 7 - row
            chess_col = col if not flipped else 7 - col
            
            square = chess.square(chess_col, chess_row)
            piece = board.piece_at(square)
            
            if piece:
                # Convert piece to image key
                color = 'w' if piece.color == chess.WHITE else 'b'
                piece_type = None
                
                if piece.piece_type == chess.PAWN:
                    piece_type = 'P'
                elif piece.piece_type == chess.KNIGHT:
                    piece_type = 'N'
                elif piece.piece_type == chess.BISHOP:
                    piece_type = 'B'
                elif piece.piece_type == chess.ROOK:
                    piece_type = 'R'
                elif piece.piece_type == chess.QUEEN:
                    piece_type = 'Q'
                elif piece.piece_type == chess.KING:
                    piece_type = 'K'
                
                image_key = color + piece_type
                if image_key in pieces:
                    image = pieces[image_key]
                    
                    # Calculate the center position of the square
                    square_center_x = offset_x + col * square_size + square_size // 2
                    square_center_y = offset_y + row * square_size + square_size // 2
                    
                    # Place the image centered on the square
                    image_rect = image.get_rect(center=(square_center_x, square_center_y))
                    screen.blit(image, image_rect)

def apply_legal_move(board, move):
    """Apply a legal move to the board."""
    if board.is_legal(move):
        board.push(move)
        return True
    return False

def draw_highlights(screen, board, selected_square, flipped, dimension, offset_y=40, offset_x=0):
    """Draw highlighted squares and legal move indicators."""
    if selected_square is None:
        return
        
    square_size = dimension
    
    # Highlight the selected square
    row = chess.square_rank(selected_square)
    col = chess.square_file(selected_square)
    if flipped:
        draw_row = row
        draw_col = 7 - col
    else:
        draw_row = 7 - row
        draw_col = col
        
    highlight_surf = p.Surface((square_size, square_size), p.SRCALPHA)
    highlight_surf.fill((255, 255, 0, 100))
    screen.blit(highlight_surf, (offset_x + draw_col * square_size, offset_y + draw_row * square_size))

def draw_legal_move_indicators(screen, board, selected_square, flipped, dimension, offset_y=40, offset_x=0):
    """Draw indicators for legal moves from the selected square."""
    if selected_square is None:
        return
        
    # Use consistent square size
    square_size = BOARD_HEIGHT // dimension
    
    for move in board.legal_moves:
        if move.from_square == selected_square:
            to_row = chess.square_rank(move.to_square)
            to_col = chess.square_file(move.to_square)
            
            # Convert chess coordinates to screen coordinates
            if flipped:
                draw_row = to_row
                draw_col = 7 - to_col
            else:
                draw_row = 7 - to_row
                draw_col = to_col
            
            # Draw a circle for the legal move
            circle_surface = p.Surface((square_size, square_size), p.SRCALPHA)
            is_capture = board.piece_at(move.to_square) is not None
            
            # Special highlight for king captures
            target = board.piece_at(move.to_square)
            if target and target.piece_type == chess.KING:
                # Bright red highlight for king capture
                p.draw.circle(circle_surface, (255, 0, 0, 180), 
                            (square_size // 2, square_size // 2), square_size // 2, 7)
            elif is_capture:
                p.draw.circle(circle_surface, (0, 0, 0, 120), 
                            (square_size // 2, square_size // 2), square_size // 2, 7)
            else:
                p.draw.circle(circle_surface, (0, 0, 0, 120), 
                            (square_size // 2, square_size // 2), square_size // 7)
            
            screen.blit(circle_surface, (offset_x + draw_col * square_size, offset_y + draw_row * square_size))
