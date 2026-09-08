def occurance_substring(main_string, sub_string):
    # Initialize variables to store the start and end positions of the substring
    start = 0
    end = 0
    # Initialize a list to store the positions of the substring
    positions = []
    # Loop through the main string to find the substring
    while end < len(main_string):
        # Find the position of the substring starting from the current end
        pos = main_string.find(sub_string, end)
        # If the substring is found, add its position to the list
        if pos != -1:
            positions.append(pos)
            # Move the end position to the next character to allow for overlapping matches
            end += 1
        else:
            break
    # Return the list of positions of the substring
    return positions