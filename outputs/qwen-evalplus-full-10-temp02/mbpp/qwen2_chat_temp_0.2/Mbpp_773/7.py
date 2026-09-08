def occurance_substring(main_string, sub_string):
    # Initialize variables to store the result
    result = None
    start = 0
    
    # Loop through the main string to find all occurrences of the sub_string
    while start <= len(main_string) - len(sub_string):
        # Check if the substring matches the current position
        if main_string[start:start+len(sub_string)] == sub_string:
            # If a match is found, store the start index and the length of the match
            result = (start, len(sub_string))
        # Move the start index to the next character to allow for overlapping matches
        start += 1
    
    # Return the result if a match was found, otherwise return None
    return result