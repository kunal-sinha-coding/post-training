import re
def find_adverb_position(sentence):
    # Use regular expression to find all occurrences of the word "clearly"
    matches = re.findall(r'\bclearly\b', sentence)
    # Initialize variables to store the position of the first adverb and its value
    first_adverb_position = -1
    first_adverb_value = ''
    # Iterate through the matches to find the first adverb
    for match in matches:
        # Check if the match is the first adverb found
        if first_adverb_position == -1 or match < first_adverb_value:
            first_adverb_position = matches.index(match)
            first_adverb_value = match
    # Return the position of the first adverb and its value
    return first_adverb_position, first_adverb_value