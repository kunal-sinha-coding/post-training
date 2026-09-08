def occurance_substring(main_str, sub_str):
    # Initialize variables to store the start and end positions of the substring
    start = 0
    end = 0
    # Iterate through the main string
    while end < len(main_str):
        # Find the position of the substring starting from the current position
        pos = main_str.find(sub_str, start)
        # If the substring is found, update the start position and end position
        if pos != -1:
            start = pos + 1
            end = pos + len(sub_str)
        else:
            # If the substring is not found, break the loop
            break
    # Return the substring and its start and end positions
    return (sub_str, start, end)
