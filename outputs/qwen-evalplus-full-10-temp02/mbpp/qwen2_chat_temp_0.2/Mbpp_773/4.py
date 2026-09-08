def occurance_substring(main_str, sub_str):
    # Initialize variables to store the result
    result = None
    start = 0
    
    # Loop through the main string
    while start <= len(main_str) - len(sub_str):
        # Check if the substring matches the current position
        if main_str[start:start+len(sub_str)] == sub_str:
            # If a match is found, update the result
            result = (sub_str, start, start+len(sub_str))
        # Move the start position to the next character
        start += 1
    
    # Return the result
    return result