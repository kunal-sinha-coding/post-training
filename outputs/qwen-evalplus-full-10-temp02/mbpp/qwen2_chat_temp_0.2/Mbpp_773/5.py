def occurance_substring(main_string, sub_string):
    # Initialize variables to store the result
    result = None
    # Start searching from the beginning of the main string
    start = 0
    # Loop through the main string
    while start <= len(main_string) - len(sub_string):
        # Check if the substring matches the current position
        if main_string[start:start+len(sub_string)] == sub_string:
            # If it matches, update the result with the current position
            result = (sub_string, start, start+len(sub_string))
        # Move the start position to the next character
        start += 1
    # Return the result
    return result