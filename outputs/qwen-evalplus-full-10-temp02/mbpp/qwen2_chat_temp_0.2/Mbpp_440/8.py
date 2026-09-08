import re

def find_adverb_position(sentence):
    # Use regular expression to find all occurrences of the word "clearly"
    matches = re.findall(r'\bclearly\b', sentence)
    # Initialize variables to store the position of the first adverb and its value
    first_adverb_position = -1
    first_adverb_value = None
    
    # Iterate through the matches to find the first adverb
    for match in matches:
        # Check if the match is not empty and if it is the first adverb found
        if match and match != first_adverb_value:
            first_adverb_position = sentence.index(match)
            first_adverb_value = match
    
    # Return the position and the value of the first adverb
    return (first_adverb_position, first_adverb_value)
