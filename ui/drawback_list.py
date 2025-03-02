import pygame as p
import chess
from GameState.drawback_manager import get_drawback_info, DRAWBACKS
from ui.components import DrawbackButton, SearchBox

class DrawbackList:
    """Component for displaying and managing a scrollable list of drawbacks."""
    def __init__(self, x, y, width, height, color, font=None):
        self.rect = p.Rect(x, y, width, height)
        self.color = color  # chess.WHITE or chess.BLACK
        self.font = font or p.font.SysFont(None, 20)
        self.buttons = []
        self.search_box = SearchBox(
            x + 20, y + 30, width - 40, 30, 
            f"Search {'White' if color == chess.WHITE else 'Black'} Drawbacks..."
        )
        
        # Add space between title, search box, and current selection
        self.title_height = 20
        self.search_height = 40  # Search box + padding
        self.selection_height = 30
        
        self.scroll_y = 0
        self.max_scroll = 0
        self.selected_drawback = None
        
        # Load initial drawbacks list
        self.populate_list()
    
    def populate_list(self, current_drawback=None):
        """Populate the list with drawback buttons based on search criteria."""
        self.buttons = []
        
        # Get all drawbacks sorted alphabetically
        all_drawbacks = sorted(DRAWBACKS.keys())
        
        # Filter drawbacks based on search query
        filtered_drawbacks = [d for d in all_drawbacks 
                             if self.search_box.text.lower() in d.lower()]
        
        # Create buttons for each drawback
        btn_height = 30
        spacing = 10
        
        # Start position for drawback buttons - below title, search box and selection info
        y_pos = self.rect.y + self.title_height + self.search_height + self.selection_height
        
        for drawback in filtered_drawbacks:
            # Get display name
            display_name = drawback.replace('_', ' ').title()
            
            # Get description if available
            drawback_info = get_drawback_info(drawback)
            description = drawback_info.get('description', '')
            
            # Create button
            btn = DrawbackButton(
                self.rect.x + 20, y_pos, self.rect.width - 40, btn_height,
                drawback, display_name, description, self.color,
                active=(drawback == current_drawback or drawback == self.selected_drawback), 
                font=self.font
            )
            
            self.buttons.append(btn)
            y_pos += btn_height + spacing
        
        # Calculate maximum scroll value
        list_height = y_pos - (self.rect.y + self.title_height + self.search_height + self.selection_height)
        self.max_scroll = max(0, list_height - (self.rect.height - self.title_height - self.search_height - self.selection_height - 20))
    
    def draw(self, surface):
        """Draw the drawback list with search box and buttons."""
        # Draw background rectangle for the section
        p.draw.rect(surface, (70, 70, 70), self.rect, 0, 5)  # Add rounded corners
        
        # Draw title
        color_name = "White" if self.color == chess.WHITE else "Black"
        title = self.font.render(f"{color_name} Drawbacks", True, (255, 255, 255))
        surface.blit(title, (self.rect.x + 20, self.rect.y + 10))
        
        # Draw search box
        self.search_box.draw(surface)
        
        # Draw current selection
        y_pos = self.rect.y + self.title_height + self.search_height
        selected_name = self.selected_drawback.replace('_', ' ').title() if self.selected_drawback else "None"
        current_text = self.font.render(f"Current: {selected_name}", True, (255, 255, 255))
        surface.blit(current_text, (self.rect.x + 20, y_pos))
        
        # Draw scroll arrows if needed
        if self.max_scroll > 0:
            # Up arrow - positioned just below title area
            p.draw.polygon(surface, (200, 200, 200), [
                (self.rect.x + self.rect.width - 30, self.rect.y + self.title_height + self.search_height + self.selection_height + 10),
                (self.rect.x + self.rect.width - 40, self.rect.y + self.title_height + self.search_height + self.selection_height + 25),
                (self.rect.x + self.rect.width - 20, self.rect.y + self.title_height + self.search_height + self.selection_height + 25)
            ])
            
            # Down arrow - near bottom of rect
            p.draw.polygon(surface, (200, 200, 200), [
                (self.rect.x + self.rect.width - 30, self.rect.y + self.rect.height - 20),
                (self.rect.x + self.rect.width - 40, self.rect.y + self.rect.height - 35),
                (self.rect.x + self.rect.width - 20, self.rect.y + self.rect.height - 35)
            ])
        
        # Draw buttons
        hover_description = None
        
        # Create a clipping rect for the buttons area
        clip_rect = p.Rect(
            self.rect.x, 
            self.rect.y + self.title_height + self.search_height + self.selection_height,
            self.rect.width, 
            self.rect.height - self.title_height - self.search_height - self.selection_height
        )
        
        old_clip = surface.get_clip()
        surface.set_clip(clip_rect)
        
        for btn in self.buttons:
            was_drawn = btn.draw(surface, self.scroll_y)
            # Check if mouse is hovering this button
            if was_drawn:  # Only check hover for visible buttons
                mouse_pos = p.mouse.get_pos()
                if btn.is_clicked(mouse_pos, self.scroll_y):
                    hover_description = btn.description
        
        # Reset clipping
        surface.set_clip(old_clip)
        
        return hover_description
    
    def handle_click(self, pos, board=None):
        """Handle mouse click events in the drawback list."""
        # Check if search box was clicked
        if self.search_box.is_clicked(pos):
            self.search_box.active = True
            return True
            
        # Check if any drawback button was clicked
        for btn in self.buttons:
            if btn.is_clicked(pos, self.scroll_y):
                if board:
                    board.set_drawback(self.color, btn.id)
                self.selected_drawback = btn.id
                
                # Update button active states
                for b in self.buttons:
                    b.active = (b.id == btn.id)
                
                return True
                
        return False
    
    def handle_key(self, event):
        """Handle key press events for search box."""
        if self.search_box.active:
            if self.search_box.handle_key(event):
                self.search_box.active = False
            # Update the list when searching
            self.populate_list()
            return True
        return False
    
    def handle_scroll(self, y_offset):
        """Handle mouse wheel scrolling."""
        self.scroll_y = max(0, min(self.max_scroll, self.scroll_y - y_offset * 20))
        return True
