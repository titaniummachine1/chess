
# When creating the drawback dropdown/selection UI element
def create_drawback_selector(parent_widget):
    # ... existing code ...
    
    # Make sure "none" is the first option and selected by default
    drawback_options = ["none"] + [d for d in AVAILABLE_DRAWBACKS if d != "none"]
    drawback_selector.set_options(drawback_options)
    drawback_selector.select("none")
    
    # ... rest of the function ...
