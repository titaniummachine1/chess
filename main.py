## main.py keep this comment its important
from GameState.gamestate import GameState  # Import GameState class
from utils import load_images, draw_board, draw_pieces, apply_legal_move, draw_highlights
import pygame as p

# Screen settings
WIDTH, HEIGHT = 680, 680
DIMENSION = 8  # Chessboard size (8x8)
SQ_SIZE = HEIGHT // DIMENSION
FPS = 12

def main():
    """Main game loop for the chess program."""
    p.init()
    screen = p.display.set_mode((WIDTH, HEIGHT))
    clock = p.time.Clock()
    game_state = GameState()  # Initialize game state
    load_images()  # Load piece images

    running = True
    flipped = True  # White at bottom
    selected_square = None  # None if no piece is selected

    while running:
        for event in p.event.get():
            if event.type == p.QUIT:
                running = False

            if event.type == p.MOUSEBUTTONDOWN:
                pos = p.mouse.get_pos()

                # Convert pixel coords to board coords (row, col)
                row = 7 - (pos[1] // SQ_SIZE) if flipped else pos[1] // SQ_SIZE
                col = 7 - (pos[0] // SQ_SIZE) if flipped else pos[0] // SQ_SIZE

                piece_data = game_state.get_piece_at(row, col)

                if selected_square is None:
                    # --- No piece selected yet ---
                    # Only select if there's a piece of our color
                    if piece_data is not None:
                        color, piece_type = piece_data
                        print(color, piece_type)
                        if color == game_state.current_turn:
                            selected_square = (row, col)
                else:
                    # --- A piece is already selected ---
                    if (row, col) == selected_square:
                        # Clicked same square -> deselect
                        selected_square = None
                    else:
                        # If clicked a piece of the same color, change selection
                        if piece_data is not None:
                            color, piece_type = piece_data
                            if color == game_state.current_turn:
                                selected_square = (row, col)
                                continue  # Do not attempt to move, just reselect

                        # Otherwise, attempt a move to this square
                        move = (selected_square, (row, col))
                        apply_legal_move(game_state, move)
                        selected_square = None  # Reset selection

            elif event.type == p.KEYDOWN:
                if event.key == p.K_r:  # Reset game
                    game_state = GameState()
                    selected_square = None
                    flipped = False

                elif event.key == p.K_f:  # Flip board
                    flipped = not flipped

        # Draw board and pieces
        draw_board(screen)
        draw_highlights(screen, game_state, selected_square, flipped=flipped)
        draw_pieces(screen, game_state, flipped=flipped)

        clock.tick(FPS)
        p.display.flip()

if __name__ == "__main__":
    main()
