import pygame as p
import chess

def run():
    """
    Displays a modal promotion selection panel.
    Returns one of: chess.QUEEN, chess.ROOK, chess.KNIGHT, or chess.BISHOP.
    """
    # Create a surface for promotion panel overlay
    screen = p.display.get_surface()
    overlay = p.Surface(screen.get_size(), p.SRCALPHA)
    overlay.fill((0, 0, 0, 180))  # semitransparent black
    screen.blit(overlay, (0,0))
    p.display.flip()

    # Load promotion images (assumed in images/ folder, similar to normal pieces)
    options = {
        "queen": {"piece": chess.QUEEN, "image": p.image.load("images/wQ.png")},
        "rook": {"piece": chess.ROOK, "image": p.image.load("images/wR.png")},
        "bishop": {"piece": chess.BISHOP, "image": p.image.load("images/wB.png")},
        "knight": {"piece": chess.KNIGHT, "image": p.image.load("images/wN.png")},
    }
    # Scale images to desired button size
    button_size = 80
    for key in options:
        options[key]["image"] = p.transform.scale(options[key]["image"], (button_size, button_size))

    # Determine positions for the 4 buttons centered horizontally and vertically
    screen_width, screen_height = screen.get_size()
    gap = 20
    total_width = 4 * button_size + 3 * gap
    start_x = (screen_width - total_width)//2
    y = (screen_height - button_size)//2
    buttons = {}
    for i, key in enumerate(options):
        rect = p.Rect(start_x + i*(button_size+gap), y, button_size, button_size)
        buttons[key] = rect
        p.draw.rect(screen, (200,200,200), rect)
        screen.blit(options[key]["image"], rect.topleft)

    p.display.flip()

    # Wait for a mouse click on one of the buttons
    selected = None
    while selected is None:
        for event in p.event.get():
            if event.type == p.MOUSEBUTTONDOWN:
                pos = event.pos
                for key, rect in buttons.items():
                    if rect.collidepoint(pos):
                        selected = options[key]["piece"]
                        break
    return selected
