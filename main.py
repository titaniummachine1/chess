##main.py do nto remove this comment you damn idiot
import pygame as p
import chess
import random
from utils import load_images, draw_board, draw_pieces, apply_legal_move, draw_highlights
from GameState.movegen import DrawbackBoard
from GameState.drawback_manager import DRAWBACKS
from AI.search import best_move

# Game Settings
WIDTH, HEIGHT = 680, 680
DIMENSION = 8
SQ_SIZE = HEIGHT // DIMENSION
FPS = 12
AI_DEPTH = 3  # Adjust AI search depth (higher = stronger)

WHITE_AI = False  # Set to True if you want White to be controlled by AI
BLACK_AI = True   # Set to True if you want Black to be controlled by AI

def assign_drawbacks(board):
    board.set_drawback(chess.WHITE, "no_knight_moves")
    board.set_drawback(chess.BLACK, "no_knight_moves")
    print("Drawbacks: no_knight_moves assigned to both players.")

def display_winner(screen, winner_color):
    """Display the winner and stop the game."""
    font = p.font.Font(None, 50)
    text = f"{'White' if winner_color == chess.WHITE else 'Black'} wins by capturing the king! Press 'R' to restart."
    text_surf = font.render(text, True, p.Color("black"), p.Color("gold"))
    text_rect = text_surf.get_rect(center=(WIDTH // 2, HEIGHT // 2))
    screen.blit(text_surf, text_rect)
    p.display.flip()

def ai_move(board):
    """Executes AI move if it's AI's turn and the game isn't over."""
    global game_over, winner_color

    if not board.is_variant_end():
        move = best_move(board, AI_DEPTH)
        if move:
            # Check if this is a king capture move
            target = board.piece_at(move.to_square)
            if target and target.piece_type == chess.KING:
                print(f"AI is capturing the {'White' if target.color == chess.WHITE else 'Black'} king!")
            
            board.push(move)
            print(f"AI moved: {move}")

            # Check if the AI won by capturing the king
            if board.is_variant_end():
                game_over = True
                winner_color = chess.WHITE if board.is_variant_win() else chess.BLACK
                print(f"Game over! {'White' if winner_color == chess.WHITE else 'Black'} wins by capturing the king!")
        else:
            print("AI has no legal moves!")

def main():
    """Main game loop for Drawback Chess."""
    p.init()
    screen = p.display.set_mode((WIDTH, HEIGHT))
    clock = p.time.Clock()
    p.display.set_caption("Drawback Chess")

    load_images()
    board = DrawbackBoard()
    assign_drawbacks(board)
    board.reset()
    
    # Print the FEN for debugging
    print(f"Starting position FEN: {board.fen()}")
    
    # Debug the initial board state
    for r in range(8):
        rank_str = ""
        for f in range(8):
            sq = chess.square(f, r)  # file (0-7), rank (0-7)
            piece = board.piece_at(sq)
            if piece:
                rank_str += piece.symbol() + " "
            else:
                rank_str += "· "
        print(f"{8-r} {rank_str}")
    print("  a b c d e f g h")

    global game_over, winner_color
    running = True

    # Default orientation: White on bottom, Black on top
    flipped = False

    selected_square = None
    game_over = False
    winner_color = None

    while running:
        for event in p.event.get():
            if event.type == p.QUIT:
                running = False

            elif event.type == p.MOUSEBUTTONDOWN and not game_over:
                # Only allow user input if the current side is not AI
                if not (WHITE_AI and board.turn == chess.WHITE) and not (BLACK_AI and board.turn == chess.BLACK):
                    x, y = event.pos
                    row, col = y // SQ_SIZE, x // SQ_SIZE

                    # Convert screen coordinates to board coordinates
                    if flipped:
                        board_row = row 
                        board_col = 7 - col
                    else:
                        board_row = 7 - row
                        board_col = col

                    clicked_square = chess.square(board_col, board_row)  # file, rank

                    if selected_square is None:
                        piece = board.piece_at(clicked_square)
                        if piece and piece.color == board.turn:
                            selected_square = clicked_square
                            print(f"Selected {piece.symbol()} at {chess.square_name(clicked_square)}")
                    else:
                        move = chess.Move(selected_square, clicked_square)
                        
                        # Check if this move captures a king
                        target = board.piece_at(clicked_square)
                        is_king_capture = target and target.piece_type == chess.KING
                        
                        if board.is_legal(move):
                            if is_king_capture:
                                print(f"Capturing the {'White' if target.color == chess.WHITE else 'Black'} king!")
                                
                            print(f"Moving {board.piece_at(selected_square).symbol()} from {chess.square_name(selected_square)} to {chess.square_name(clicked_square)}")
                            board.push(move)
                            selected_square = None
                            
                            # Check if the move resulted in a king capture (game over)
                            if board.is_variant_end():
                                winner_color = chess.WHITE if board.is_variant_win() else chess.BLACK
                                game_over = True
                        else:
                            # Check if clicked on another piece of same color
                            piece = board.piece_at(clicked_square)
                            if piece and piece.color == board.turn:
                                selected_square = clicked_square
                                print(f"Selected {piece.symbol()} at {chess.square_name(clicked_square)}")
                            else:
                                print(f"Illegal move: {chess.square_name(selected_square)} to {chess.square_name(clicked_square)}")
                                selected_square = None

            elif event.type == p.KEYDOWN:
                if event.key == p.K_f:
                    # Flip the board
                    flipped = not flipped
                    print("Board flipping:", flipped)
                elif event.key == p.K_r:
                    # Reset board and game state properly
                    board = DrawbackBoard()
                    assign_drawbacks(board)
                    board.reset()

                    selected_square = None
                    game_over = False
                    winner_color = None

                    print("Game restarted!")

        if not game_over:
            # Let AI move if it's AI's turn
            if BLACK_AI and board.turn == chess.BLACK:
                ai_move(board)
            if WHITE_AI and board.turn == chess.WHITE:
                ai_move(board)

        draw_board(screen, DIMENSION, WIDTH, HEIGHT, flipped)
        draw_pieces(screen, board, flipped, DIMENSION)
        
        # Highlight the selected square
        if selected_square is not None:
            row = chess.square_rank(selected_square)
            col = chess.square_file(selected_square)
            if flipped:
                draw_row = row
                draw_col = 7 - col
            else:
                draw_row = 7 - row
                draw_col = col
                
            highlight_surf = p.Surface((SQ_SIZE, SQ_SIZE), p.SRCALPHA)
            highlight_surf.fill((255, 255, 0, 100))
            screen.blit(highlight_surf, (draw_col * SQ_SIZE, draw_row * SQ_SIZE))
            
            # Also highlight legal moves
            for move in board.legal_moves:
                if move.from_square == selected_square:
                    to_row = chess.square_rank(move.to_square)
                    to_col = chess.square_file(move.to_square)
                    
                    if flipped:
                        to_draw_row = to_row
                        to_draw_col = 7 - to_col
                    else:
                        to_draw_row = 7 - to_row
                        to_draw_col = to_col
                    
                    # Draw a circle for the legal move
                    circle_surface = p.Surface((SQ_SIZE, SQ_SIZE), p.SRCALPHA)
                    is_capture = board.piece_at(move.to_square) is not None
                    
                    # Special highlight for king captures
                    target = board.piece_at(move.to_square)
                    if target and target.piece_type == chess.KING:
                        # Bright red highlight for king capture
                        p.draw.circle(circle_surface, (255, 0, 0, 180), 
                                    (SQ_SIZE // 2, SQ_SIZE // 2), SQ_SIZE // 2, 7)
                    elif is_capture:
                        p.draw.circle(circle_surface, (0, 0, 0, 120), 
                                    (SQ_SIZE // 2, SQ_SIZE // 2), SQ_SIZE // 2, 7)
                    else:
                        p.draw.circle(circle_surface, (0, 0, 0, 120), 
                                    (SQ_SIZE // 2, SQ_SIZE // 2), SQ_SIZE // 7)
                    screen.blit(circle_surface, (to_draw_col * SQ_SIZE, to_draw_row * SQ_SIZE))

        if game_over and winner_color is not None:
            display_winner(screen, winner_color)

        clock.tick(FPS)
        p.display.flip()

    p.quit()

if __name__ == "__main__":
    main()
