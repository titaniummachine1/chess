import pygame as p
import chess
import random
from utils import load_images, draw_board, draw_pieces, apply_legal_move, draw_highlights
from GameState.movegen import DrawbackBoard
from GameState.drawback_manager import DRAWBACKS

# Game Settings
WIDTH, HEIGHT = 680, 680
DIMENSION = 8
SQ_SIZE = HEIGHT // DIMENSION
FPS = 15

def assign_random_drawbacks(board):
    """Assigns the 'no_knight_moves' drawback to both players."""
    
    drawback = "no_knight_moves"  # Set fixed drawback for both players
    
    board.set_drawback(chess.WHITE, drawback)
    board.set_drawback(chess.BLACK, drawback)

    # Debug print
    print(f"Assigned drawback - White: {drawback}, Black: {drawback}")

# Display winner message and wait for restart
def display_winner(screen, winner_color):
    font = p.font.Font(None, 50)
    text = f"{'White' if winner_color == chess.WHITE else 'Black'} wins! Press 'R' to restart."
    text_surf = font.render(text, True, p.Color("black"), p.Color("gold"))
    text_rect = text_surf.get_rect(center=(WIDTH // 2, HEIGHT // 2))
    screen.blit(text_surf, text_rect)
    p.display.flip()

# Main game loop
def main():
    p.init()
    screen = p.display.set_mode((WIDTH, HEIGHT))
    clock = p.time.Clock()
    p.display.set_caption("Drawback Chess")

    load_images()
    board = DrawbackBoard()
    board.reset()  # Reset first to ensure a clean state
    assign_random_drawbacks(board)  # Then assign drawbacks

    running = True
    flipped = True
    selected_square = None
    game_over = False  # Track if the game is over
    winner_color = None  # Store winner color to display properly

    while running:
        for event in p.event.get():
            if event.type == p.QUIT:
                running = False

            elif event.type == p.MOUSEBUTTONDOWN and not game_over:
                x, y = event.pos
                row, col = y // SQ_SIZE, x // SQ_SIZE
                if flipped:
                    row, col = 7 - row, 7 - col
                clicked_square = row * 8 + col

                if selected_square is None:
                    # Selecting a piece
                    if board.piece_at(clicked_square) and board.color_at(clicked_square) == board.turn:
                        selected_square = (row, col)
                else:
                    # Handle clicks intelligently
                    move_coords = (selected_square, (row, col))
                    new_selected_square = apply_legal_move(board, move_coords, selected_square)
                    selected_square = new_selected_square  # Update selection based on logic

                    # Ensure the board updates before checking for game end
                    draw_board(screen, DIMENSION, WIDTH, HEIGHT)
                    draw_pieces(screen, board, flipped, DIMENSION)
                    p.display.flip()

                    # Check for game end
                    if board.is_variant_end():
                        winner_color = chess.WHITE if board.is_variant_win() else chess.BLACK
                        game_over = True

            elif event.type == p.KEYDOWN:
                if event.key == p.K_f:
                    flipped = not flipped  # Flip board
                elif event.key == p.K_r:
                    board.reset()
                    assign_random_drawbacks(board)
                    selected_square = None
                    game_over = False  # Reset game state
                    winner_color = None  # Reset winner message

        # Drawing board and pieces
        draw_board(screen, DIMENSION, WIDTH, HEIGHT)
        if selected_square is not None:
            draw_highlights(screen, board, selected_square, flipped)
        draw_pieces(screen, board, flipped, DIMENSION)

        # Display winner screen without disappearing instantly
        if game_over and winner_color is not None:
            display_winner(screen, winner_color)

        clock.tick(FPS)
        p.display.flip()

    p.quit()

if __name__ == "__main__":
    main()
