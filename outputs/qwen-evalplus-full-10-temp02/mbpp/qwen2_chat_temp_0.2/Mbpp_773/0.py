def occurance_substring(main_string, sub_string):
    # Initialize variables to store the occurrence and position of the substring
    occurrence = None
    position = None
    
    # Iterate through the main string to find the substring
    for i in range(len(main_string) - len(sub_string) + 1):
        # Check if the substring matches the current position
        if main_string[i:i+len(sub_string)] == sub_string:
            # Update the occurrence and position
            occurrence = i
            position = i + len(sub_string)
    
    # Return the occurrence and position
    return (occurrence, position)
