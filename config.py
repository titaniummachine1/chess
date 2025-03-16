"""
Drawback Chess Configuration File
Edit this file to customize your game settings.
Changes take effect when you restart the program.
"""
import json
import os
import sys

# Default configuration
DEFAULT_CONFIG = {
    # Game position settings
    "position": {
        "name": "initial",  # Options: "initial", "endgame", "middlegame", "capture_test", "complex", "kings_adjacent", "atomic_bomb_test"
        "custom_fen": "",   # Optionally provide a custom FEN string here (will override position name if not empty)
    },
    
    # Drawback settings
    "drawbacks": {
        "white": "",  # Leave empty for no drawback
        "black": "",  # Leave empty for no drawback
    },
    
    # AI settings
    "ai": {
        "white_ai": False,  # Set to True to make AI play as white
        "black_ai": True,   # Set to True to make AI play as black
        "depth": 7,         # Search depth (higher = stronger but slower)
        "time_limit": 10,   # Time limit in seconds for AI moves
        "smart_time_management": True  # Dynamically adjust time based on position complexity
    },
    
    # UI settings
    "ui": {
        "flip_board": False  # Flips the board view (black at bottom)
    }
}

# Configuration file path
CONFIG_FILE = "chess_config.json"

def load_config():
    """Load configuration from file or create default if it doesn't exist"""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
                
                # Update with any missing fields from default config
                merged_config = DEFAULT_CONFIG.copy()
                
                # Helper function to recursively update the config
                def update_dict(target, source):
                    for key, value in source.items():
                        if isinstance(value, dict) and key in target and isinstance(target[key], dict):
                            update_dict(target[key], value)
                        else:
                            target[key] = value
                            
                update_dict(merged_config, config)
                return merged_config
        except Exception as e:
            print(f"Error loading config file: {e}")
            print("Using default configuration")
            return DEFAULT_CONFIG
    else:
        # Create a default config file
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG

def save_config(config):
    """Save configuration to file"""
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=4)
        print(f"Configuration saved to {CONFIG_FILE}")
    except Exception as e:
        print(f"Error saving config file: {e}")

# Global configuration object
config = load_config()

def get_position():
    """Get the position name or custom FEN from config"""
    if config["position"]["custom_fen"]:
        return config["position"]["custom_fen"]
    return config["position"]["name"]

def get_white_drawback():
    """Get the white drawback or None if not specified"""
    return config["drawbacks"]["white"] or None

def get_black_drawback():
    """Get the black drawback or None if not specified"""
    return config["drawbacks"]["black"] or None

def get_ai_settings():
    """Get the AI settings as a dictionary"""
    return config["ai"]

def get_ui_settings():
    """Get the UI settings as a dictionary"""
    return config["ui"]

def save_current_settings(position, white_drawback, black_drawback, ai_settings, ui_settings):
    """Save the current game settings to the config file"""
    config["position"]["name"] = position if isinstance(position, str) else "custom"
    if isinstance(position, str) and len(position) > 8 and " " in position:
        # Likely a FEN string
        config["position"]["custom_fen"] = position
    else:
        config["position"]["custom_fen"] = ""
        
    config["drawbacks"]["white"] = white_drawback or ""
    config["drawbacks"]["black"] = black_drawback or ""
    
    # Update AI settings
    for key, value in ai_settings.items():
        if key.lower() in config["ai"]:
            config["ai"][key.lower()] = value
            
    # Update UI settings
    if "flip_board" in ui_settings:
        config["ui"]["flip_board"] = ui_settings["flip_board"]
        
    save_config(config)

# Create the config file if it doesn't exist
if not os.path.exists(CONFIG_FILE):
    save_config(DEFAULT_CONFIG)
    print(f"Created default configuration file: {CONFIG_FILE}")
    print("You can edit this file to customize your game settings.")

# Print loaded config for reference
print("\nCurrent Configuration:")
print(f"Position: {get_position()}")
print(f"White Drawback: {get_white_drawback() or 'None'}")
print(f"Black Drawback: {get_black_drawback() or 'None'}")
print(f"AI Controls White: {config['ai']['white_ai']}")
print(f"AI Controls Black: {config['ai']['black_ai']}")
print(f"Board Flipped: {config['ui']['flip_board']}\n") 