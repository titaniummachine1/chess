import pygame as p
import sys
import os
import chess
from GameState.drawback_manager import get_drawback_info, DRAWBACKS

class TinkerPanel:
    """
    A simplified separate control panel for selecting drawbacks without pygame_gui dependency.
    Features:
    - Split screen with White drawbacks on left, Black on right
    - Search functionality to find drawbacks by name
    - Immediate application of selected drawbacks to the game
    """
    def __init__(self, width=800, height=600, board_reference=None, callback=None):
        self.width = width
        self.height = height
        self.board = board_reference  # Reference to the chess board
        self.callback = callback  # Callback to update the main game
        
        # Initialize Pygame if not already done
        if not p.get_init():
            p.init()
        
        # Create the window
        self.window = p.display.set_mode((width, height), p.RESIZABLE)
        p.display.set_caption("Drawback Chess - Tinker's Control Panel")
        
        # Current search queries
        self.white_search = ""
        self.black_search = ""
        
        # Currently selected drawbacks
        self.selected_white_drawback = None
        self.selected_black_drawback = None
        
        # Font settings
        self.title_font = p.font.SysFont(None, 36)
        self.normal_font = p.font.SysFont(None, 24)
        self.small_font = p.font.SysFont(None, 20)
        
        # UI areas
        self.white_area = p.Rect(20, 60, int(width/2) - 30, height - 80)
        self.black_area = p.Rect(int(width/2) + 10, 60, int(width/2) - 30, height - 80)
        self.close_rect = p.Rect(width/2 - 60, height - 60, 120, 40)
        
        # Lists for drawback buttons
        self.white_buttons = []
        self.black_buttons = []
        
        # Text input areas
        self.white_search_rect = p.Rect(40, 100, 260, 30)
        self.black_search_rect = p.Rect(int(width/2) + 30, 100, 260, 30)
        
        # Scrolling parameters
        self.white_scroll_y = 0
        self.black_scroll_y = 0
        self.max_white_scroll = 0
        self.max_black_scroll = 0
        
        # Active text input (None, 'white', or 'black')
        self.active_input = None
        
        # Running flag
        self.running = True
        
        # Clock for limiting frame rate
        self.clock = p.time.Clock()
        
        # Load current drawbacks from the board if available
        self.load_current_drawbacks()
        
        # Populate drawback lists
        self.populate_drawbacks_lists()
    
    def load_current_drawbacks(self):
        """Load the current drawbacks from the board"""
        if self.board:
            white_drawback = self.board.get_active_drawback(chess.WHITE)
            black_drawback = self.board.get_active_drawback(chess.BLACK)
            
            if white_drawback:
                self.selected_white_drawback = white_drawback
            
            if black_drawback:
                self.selected_black_drawback = black_drawback
    
    def populate_drawbacks_lists(self):
        """Populate the drawbacks lists based on search queries"""
        # Clear existing buttons
        self.white_buttons = []
        self.black_buttons = []
        
        # Get all drawbacks sorted alphabetically
        all_drawbacks = sorted(DRAWBACKS.keys())
        
        # Filter drawbacks based on search queries
        white_drawbacks = [d for d in all_drawbacks if self.white_search.lower() in d.lower()]
        black_drawbacks = [d for d in all_drawbacks if self.black_search.lower() in d.lower()]
        
        # Create White drawback buttons
        btn_height = 30
        spacing = 10
        y_pos = 180
        
        for drawback in white_drawbacks:
            # Get display name
            display_name = drawback.replace('_', ' ').title()
            
            # Create button rect
            btn_rect = p.Rect(40, y_pos, 260, btn_height)
            
            # Add to list with metadata
            self.white_buttons.append({
                'rect': btn_rect,
                'text': display_name,
                'id': drawback,
                'color': chess.WHITE,
                'active': self.selected_white_drawback == drawback
            })
            
            y_pos += btn_height + spacing
        
        # Store max scroll value for white buttons
        self.max_white_scroll = max(0, y_pos - self.height + 60)
        
        # Create Black drawback buttons
        y_pos = 180
        
        for drawback in black_drawbacks:
            # Get display name
            display_name = drawback.replace('_', ' ').title()
            
            # Create button rect
            btn_rect = p.Rect(int(self.width/2) + 30, y_pos, 260, btn_height)
            
            # Add to list with metadata
            self.black_buttons.append({
                'rect': btn_rect,
                'text': display_name,
                'id': drawback,
                'color': chess.BLACK,
                'active': self.selected_black_drawback == drawback
            })
            
            y_pos += btn_height + spacing
        
        # Store max scroll value for black buttons
        self.max_black_scroll = max(0, y_pos - self.height + 60)
    
    def apply_drawback(self, drawback_id, color):
        """Apply the selected drawback to the specified player"""
        if self.board:
            self.board.set_drawback(color, drawback_id)
            
            # Update selected drawbacks
            if color == chess.WHITE:
                self.selected_white_drawback = drawback_id
            else:
                self.selected_black_drawback = drawback_id
            
            # Update UI
            self.populate_drawbacks_lists()
    
    def draw(self):
        """Draw the UI"""
        # Fill background
        self.window.fill((50, 50, 50))  # Dark gray
        
        # Draw title
        title_surf = self.title_font.render("Drawback Chess - Tinker's Control Panel", True, (255, 255, 255))
        title_rect = title_surf.get_rect(center=(self.width/2, 30))
        self.window.blit(title_surf, title_rect)
        
        # Draw divider line
        p.draw.line(self.window, (150, 150, 150), (self.width/2, 60), (self.width/2, self.height - 70), 2)
        
        # Draw white section title
        white_title = self.normal_font.render("White Drawbacks", True, (255, 255, 255))
        self.window.blit(white_title, (40, 60))
        
        # Draw black section title
        black_title = self.normal_font.render("Black Drawbacks", True, (255, 255, 255))
        self.window.blit(black_title, (int(self.width/2) + 30, 60))
        
        # Draw search boxes
        p.draw.rect(self.window, (200, 200, 200), self.white_search_rect, 0 if self.active_input == 'white' else 2)
        p.draw.rect(self.window, (200, 200, 200), self.black_search_rect, 0 if self.active_input == 'black' else 2)
        
        # Draw search text
        white_search_surf = self.normal_font.render(self.white_search, True, (0, 0, 0))
        black_search_surf = self.normal_font.render(self.black_search, True, (0, 0, 0))
        
        self.window.blit(white_search_surf, (self.white_search_rect.x + 5, self.white_search_rect.y + 5))
        self.window.blit(black_search_surf, (self.black_search_rect.x + 5, self.black_search_rect.y + 5))
        
        # Draw search placeholders if empty
        if not self.white_search:
            placeholder = self.small_font.render("Search White Drawbacks...", True, (120, 120, 120))
            self.window.blit(placeholder, (self.white_search_rect.x + 5, self.white_search_rect.y + 7))
        
        if not self.black_search:
            placeholder = self.small_font.render("Search Black Drawbacks...", True, (120, 120, 120))
            self.window.blit(placeholder, (self.black_search_rect.x + 5, self.black_search_rect.y + 7))
        
        # Draw current selections
        white_curr = self.normal_font.render(
            f"Current: {self.selected_white_drawback.replace('_', ' ').title() if self.selected_white_drawback else 'None'}", 
            True, (255, 255, 255)
        )
        black_curr = self.normal_font.render(
            f"Current: {self.selected_black_drawback.replace('_', ' ').title() if self.selected_black_drawback else 'None'}", 
            True, (255, 255, 255)
        )
        
        self.window.blit(white_curr, (40, 140))
        self.window.blit(black_curr, (int(self.width/2) + 30, 140))
        
        # Draw white drawback buttons (with scrolling)
        for button in self.white_buttons:
            # Adjust for scrolling
            adjusted_rect = p.Rect(
                button['rect'].x, 
                button['rect'].y - self.white_scroll_y, 
                button['rect'].width, 
                button['rect'].height
            )
            
            # Only draw if in view
            if adjusted_rect.y >= 170 and adjusted_rect.y <= self.height - 70:
                # Draw button
                color = (150, 150, 255) if button['active'] else (100, 100, 100)
                p.draw.rect(self.window, color, adjusted_rect)
                
                # Draw button text
                text_surf = self.small_font.render(button['text'], True, (255, 255, 255))
                text_rect = text_surf.get_rect(midleft=(adjusted_rect.x + 10, adjusted_rect.y + adjusted_rect.height/2))
                self.window.blit(text_surf, text_rect)
        
        # Draw black drawback buttons (with scrolling)
        for button in self.black_buttons:
            # Adjust for scrolling
            adjusted_rect = p.Rect(
                button['rect'].x, 
                button['rect'].y - self.black_scroll_y, 
                button['rect'].width, 
                button['rect'].height
            )
            
            # Only draw if in view
            if adjusted_rect.y >= 170 and adjusted_rect.y <= self.height - 70:
                # Draw button
                color = (150, 150, 255) if button['active'] else (100, 100, 100)
                p.draw.rect(self.window, color, adjusted_rect)
                
                # Draw button text
                text_surf = self.small_font.render(button['text'], True, (255, 255, 255))
                text_rect = text_surf.get_rect(midleft=(adjusted_rect.x + 10, adjusted_rect.y + adjusted_rect.height/2))
                self.window.blit(text_surf, text_rect)
        
        # Draw scroll indicators if needed
        if self.max_white_scroll > 0:
            # Draw up/down arrows
            p.draw.polygon(self.window, (200, 200, 200), [(30, 200), (20, 220), (40, 220)])
            p.draw.polygon(self.window, (200, 200, 200), [(30, self.height - 100), (20, self.height - 120), (40, self.height - 120)])
        
        if self.max_black_scroll > 0:
            # Draw up/down arrows
            x_offset = int(self.width/2) + 5
            p.draw.polygon(self.window, (200, 200, 200), [(x_offset + 10, 200), (x_offset, 220), (x_offset + 20, 220)])
            p.draw.polygon(self.window, (200, 200, 200), [(x_offset + 10, self.height - 100), (x_offset, self.height - 120), (x_offset + 20, self.height - 120)])
        
        # Draw close button
        p.draw.rect(self.window, (150, 50, 50), self.close_rect)
        close_text = self.normal_font.render("Close", True, (255, 255, 255))
        close_rect = close_text.get_rect(center=self.close_rect.center)
        self.window.blit(close_text, close_rect)
        
        # Update display
        p.display.flip()
    
    def handle_mouse_click(self, pos):
        """Handle mouse click events"""
        x, y = pos
        
        # Check if clicked on close button
        if self.close_rect.collidepoint(x, y):
            self.running = False
            return
        
        # Check if clicked on white search box
        if self.white_search_rect.collidepoint(x, y):
            self.active_input = 'white'
            return
        
        # Check if clicked on black search box
        if self.black_search_rect.collidepoint(x, y):
            self.active_input = 'black'
            return
        
        # Deactivate text input if clicked elsewhere
        self.active_input = None
        
        # Check white drawback buttons (with scrolling adjustment)
        for button in self.white_buttons:
            adjusted_rect = p.Rect(
                button['rect'].x, 
                button['rect'].y - self.white_scroll_y, 
                button['rect'].width, 
                button['rect'].height
            )
            
            if adjusted_rect.collidepoint(x, y):
                self.apply_drawback(button['id'], chess.WHITE)
                return
        
        # Check black drawback buttons (with scrolling adjustment)
        for button in self.black_buttons:
            adjusted_rect = p.Rect(
                button['rect'].x, 
                button['rect'].y - self.black_scroll_y, 
                button['rect'].width, 
                button['rect'].height
            )
            
            if adjusted_rect.collidepoint(x, y):
                self.apply_drawback(button['id'], chess.BLACK)
                return
    
    def handle_key_press(self, key, unicode_char):
        """Handle key press events"""
        if self.active_input == 'white':
            if key == p.K_BACKSPACE:
                self.white_search = self.white_search[:-1]
            elif key == p.K_RETURN:
                self.populate_drawbacks_lists()
                self.active_input = None
            else:
                self.white_search += unicode_char
            self.populate_drawbacks_lists()
        
        elif self.active_input == 'black':
            if key == p.K_BACKSPACE:
                self.black_search = self.black_search[:-1]
            elif key == p.K_RETURN:
                self.populate_drawbacks_lists()
                self.active_input = None
            else:
                self.black_search += unicode_char
            self.populate_drawbacks_lists()
    
    def handle_mouse_wheel(self, y):
        """Handle mouse wheel scrolling"""
        mouse_x, _ = p.mouse.get_pos()
        
        # If mouse is in white area
        if mouse_x < self.width/2:
            self.white_scroll_y = max(0, min(self.max_white_scroll, self.white_scroll_y - y * 20))
        # If mouse is in black area
        else:
            self.black_scroll_y = max(0, min(self.max_black_scroll, self.black_scroll_y - y * 20))
    
    def run(self):
        """Main loop for the Tinker's Control Panel"""
        while self.running:
            for event in p.event.get():
                if event.type == p.QUIT:
                    self.running = False
                
                elif event.type == p.MOUSEBUTTONDOWN:
                    if event.button == 1:  # Left click
                        self.handle_mouse_click(event.pos)
                    elif event.button == 4:  # Scroll up
                        self.handle_mouse_wheel(1)
                    elif event.button == 5:  # Scroll down
                        self.handle_mouse_wheel(-1)
                
                elif event.type == p.KEYDOWN:
                    if event.key == p.K_ESCAPE:
                        self.running = False
                    else:
                        self.handle_key_press(event.key, event.unicode)
            
            # Draw the UI
            self.draw()
            
            # Cap the frame rate
            self.clock.tick(60)
        
        # Properly close only this window, not the entire application
        pygame_window = p.display.get_surface()
        return (self.selected_white_drawback, self.selected_black_drawback)
