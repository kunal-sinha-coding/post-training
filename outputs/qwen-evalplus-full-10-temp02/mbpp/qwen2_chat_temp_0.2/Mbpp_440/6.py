import re

def find_adverb_position(sentence):
    # Use regular expression to find all occurrences of adverbs
    adverbs = re.findall(r'\b\w+\b\w+\b', sentence)
    # Initialize variables to store the position of the first adverb and its value
    first_adverb_position = -1
    first_adverb_value = None
    
    # Iterate through each adverb found
    for i, adverb in enumerate(adverbs):
        # Check if the current adverb is the first one found
        if first_adverb_position == -1 or adverb < first_adverb_value:
            first_adverb_position = i
            first_adverb_value = adverb
    
    # Return the position of the first adverb and its value
    return first_adverb_position, first_adverb_value
