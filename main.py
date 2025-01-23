import pygame as p
import chess
import random
from utils import load_images, draw_board, draw_pieces, apply_legal_move, draw_highlights
from GameState.movegen import DrawbackBoard
from GameState.drawback_manager import get_drawback_info

# Game Settings
WIDTH, HEIGHT = 680, 680
DIMENSION = 8
SQ_SIZE = HEIGHT // DIMENSION
FPS = 15

# Assign random drawbacks
def assign_random_drawbacks(board):
    available_drawbacks = list(get_drawback_info("").keys())
    board.set_drawback(chess.WHITE, random.choice(available_drawbacks))
    board.set_drawback(chess.BLACK, None)  # Opponent's drawback is unknown

# Display winner message
def display_winner(screen, winner_color):
    font = p.font.Font(None, 50)
    text = f"{'White' if winner_color == chess.WHITE else 'Black'} wins!"
    text_surf = font.render(text, True, p.Color("black"), p.Color("gold"))
    text_rect = text_surf.get_rect(center=(WIDTH // 2, HEIGHT // 2))
    screen.blit(text_surf, text_rect)
    p.display.flip()
    p.time.delay(3000)

# Main game loop
def main():
    p.init()
    screen = p.display.set_mode((WIDTH, HEIGHT))
    clock = p.time.Clock()
    p.display.set_caption("Drawback Chess")

    load_images()
    board = DrawbackBoard()
    assign_random_drawbacks(board)

    running = True
    flipped = True
    selected_square = None

    while running:
        for event in p.event.get():
            if event.type == p.QUIT:
                running = False

            elif event.type == p.MOUSEBUTTONDOWN:
                if board.is_variant_end():
                    continue  # Stop input if game has ended

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
                    # Attempting a move
                    move_coords = (selected_square, (row, col))
                    apply_legal_move(board, move_coords)
                    selected_square = None

                    # Check for game end
                    if board.is_variant_end():
                        winner = chess.WHITE if board.is_variant_win() else chess.BLACK
                        display_winner(screen, winner)
                        running = False

            elif event.type == p.KEYDOWN:
                if event.key == p.K_f:
                    flipped = not flipped  # Flip board
                elif event.key == p.K_r:
                    board.reset()
                    assign_random_drawbacks(board)
                    selected_square = None

        # Drawing board and pieces
        draw_board(screen, DIMENSION, WIDTH, HEIGHT)
        draw_highlights(screen, board, selected_square, flipped)
        draw_pieces(screen, board, flipped, DIMENSION)

        clock.tick(FPS)
        p.display.flip()

    p.quit()

if __name__ == "__main__":
    main()
