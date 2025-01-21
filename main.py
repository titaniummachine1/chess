# main.py
import pygame as p
import chess
from utils import load_images, draw_board, draw_pieces, apply_legal_move, draw_highlights

WIDTH, HEIGHT = 680, 680
DIMENSION = 8
SQ_SIZE = HEIGHT // DIMENSION
FPS = 15

def main():
    p.init()
    screen = p.display.set_mode((WIDTH, HEIGHT))
    clock = p.time.Clock()
    p.display.set_caption("Chess with python-chess")

    load_images()
    board = chess.Board()

    running = True
    flipped = True
    selected_square = None

    while running:
        for event in p.event.get():
            if event.type == p.QUIT:
                running = False

            elif event.type == p.MOUSEBUTTONDOWN:
                x, y = event.pos
                row = y // SQ_SIZE
                col = x // SQ_SIZE
                if flipped:
                    row = 7 - row
                    col = 7 - col

                if selected_square is None:
                    # We are picking up a piece
                    if board.piece_at(row*8 + col):
                        # Check if it's the side to move
                        if board.color_at(row*8 + col) == board.turn:
                            selected_square = (row, col)
                else:
                    # We have a piece selected => try the move
                    move_coords = (selected_square, (row, col))
                    apply_legal_move(board, move_coords)
                    selected_square = None

            elif event.type == p.KEYDOWN:
                if event.key == p.K_f:
                    flipped = not flipped
                elif event.key == p.K_r:
                    board.reset()
                    selected_square = None

        draw_board(screen, DIMENSION, WIDTH, HEIGHT)
        draw_highlights(screen, board, selected_square, flipped)
        draw_pieces(screen, board, flipped, DIMENSION)

        clock.tick(FPS)
        p.display.flip()

    p.quit()


if __name__ == "__main__":
    main()
