import re

def find_adverb_position(sentence):
    # Use regular expression to find all occurrences of the word "clearly"
    matches = re.findall(r'\bclearly\b', sentence)
    # Initialize variables to store the position of the first adverb and its value
    position = 0
    adverb = None
    # Iterate through the matches to find the first adverb
    for match in matches:
        # Check if the match is the first adverb found
        if position == 0:
            adverb = match
            break
        # Move to the next match
        position += 1
    # Return the position of the first adverb and its value
    return position, adverb
