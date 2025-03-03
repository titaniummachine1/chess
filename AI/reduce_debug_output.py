"""
Utility to reduce excessive debug output from the chess engine
"""
import os
import sys
import re

class OutputFilter:
    """
    Filter to limit repetitive debug output
    Reduces console spam while preserving important information
    """
    def __init__(self):
        self.previous_output = ""
        self.repeat_count = 0
        self.max_repeated_output = 3  # Show at most 3 repetitions
        self.silent = False
        self.original_stdout = sys.stdout
        
        # Patterns to filter
        self.filter_patterns = [
            r"DEBUG EVAL: Using book weights with \d+ book moves",
            r"DEBUG: \d+ nodes searched",
        ]
        
        # Compiled regex patterns
        self.compiled_patterns = [re.compile(pattern) for pattern in self.filter_patterns]
        
    def enable(self):
        """Enable output filtering"""
        sys.stdout = self
        return self
        
    def disable(self):
        """Disable output filtering"""
        sys.stdout = self.original_stdout
        return self
        
    def set_silent(self, silent):
        """Set silent mode - no output at all"""
        self.silent = silent
        return self
        
    def write(self, text):
        """Filter and write output"""
        if self.silent:
            return
            
        # Check if this is a filtered pattern
        for pattern in self.compiled_patterns:
            if pattern.search(text):
                # This is a pattern we want to filter
                if text == self.previous_output:
                    self.repeat_count += 1
                    if self.repeat_count <= self.max_repeated_output:
                        self.original_stdout.write(text)
                    elif self.repeat_count == self.max_repeated_output + 1:
                        self.original_stdout.write(f"... (further similar messages suppressed) ...\n")
                    return
                else:
                    self.previous_output = text
                    self.repeat_count = 1
                    self.original_stdout.write(text)
                    return
        
        # Not a filtered pattern, write normally
        self.previous_output = ""  # Reset repeat tracking
        self.repeat_count = 0
        self.original_stdout.write(text)
        
    def flush(self):
        """Pass through flush calls"""
        self.original_stdout.flush()

# Create a singleton instance
OUTPUT_FILTER = OutputFilter()

def enable_output_filtering():
    """Enable output filtering to reduce console spam"""
    OUTPUT_FILTER.enable()
    print("Debug output filtering enabled - reducing console spam")
    
def disable_output_filtering():
    """Disable output filtering"""
    OUTPUT_FILTER.disable()
    print("Debug output filtering disabled - showing all console output")

# Auto-enable when imported
enable_output_filtering()
