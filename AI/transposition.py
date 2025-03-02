import random
from collections import OrderedDict

class BoundedTranspositionTable:
    """
    A fixed-size transposition table that evicts oldest entries when capacity is reached.
    Uses an OrderedDict to track the age of entries.
    """
    def __init__(self, capacity=2**20):
        self.capacity = capacity
        self.table = OrderedDict()
    
    def store(self, key, value):
        """
        Store an entry in the transposition table, evicting oldest entry if capacity reached.
        """
        # If table is full, remove oldest item (first item in OrderedDict)
        if len(self.table) >= self.capacity:
            self.table.popitem(last=False)
            
        # Store new entry
        self.table[key] = value
        
    def retrieve(self, key):
        """
        Retrieve an entry from the transposition table.
        Returns None if key not found.
        """
        if key in self.table:
            # Move the accessed item to the end (marking it as most recently used)
            value = self.table.pop(key)
            self.table[key] = value
            return value
        return None
    
    def clear(self):
        """Clear all entries from the table."""
        self.table.clear()
        
    def __len__(self):
        """Return the current number of entries in the table."""
        return len(self.table)
