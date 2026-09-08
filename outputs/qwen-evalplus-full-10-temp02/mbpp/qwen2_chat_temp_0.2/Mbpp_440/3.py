import re
def find_adverb_position(sentence):
    # Use regular expression to find all occurrences of the word "clearly"
    matches = re.findall(r'\bclearly\b', sentence)
    # Initialize variables to store the position of the first adverb and its value
    position = -1
    value = None
    # Iterate through the matches to find the first adverb
    for match in matches:
        # Check if the match is the first adverb found
        if position == -1:
            position = sentence.index(match)
            value = match
    # Return the position and the value of the first adverb
    return position, value
