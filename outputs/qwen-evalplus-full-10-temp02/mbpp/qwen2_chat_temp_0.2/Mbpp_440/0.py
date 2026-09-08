import re

def find_adverb_position(sentence):
    # Use regular expression to find all occurrences of the word 'clearly'
    matches = re.findall(r'\bclearly\b', sentence)
    # Initialize variables to store the position of the first adverb and its value
    position = 0
    adverb = None
    
    # Iterate through the matches to find the first adverb
    for match in matches:
        # Check if the match is not the first one
        if position != 0:
            # Update the position and the adverb
            position = match.start()
            adverb = match.group()
        else:
            # Update the position if it's the first match
            position = match.start()
    
    return position, adverb
