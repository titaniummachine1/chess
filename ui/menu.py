
# Add "none" to the list of available drawbacks
AVAILABLE_DRAWBACKS = [
    "none",  # No drawbacks (default)
    "no_knight_moves",  # Knights cannot move
    "no_bishop_captures",  # Bishops cannot capture pieces
    "no_knight_captures",  # Knights cannot capture pieces
    # ... other existing drawbacks ...
]

# Make sure the default selection is "none"
DEFAULT_DRAWBACK = "none"

# When initializing drawbacks in your code, ensure "none" is handled properly:
def get_selected_drawbacks():
    # ... existing code ...
    
    # If "none" is selected, return None or empty list based on your implementation
    if selected_drawback == "none":
        return None  # or return [] depending on how your code handles drawbacks
    
    # ... rest of the function ...
