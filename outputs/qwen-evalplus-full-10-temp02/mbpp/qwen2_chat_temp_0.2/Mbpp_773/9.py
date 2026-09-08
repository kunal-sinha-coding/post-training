def occurance_substring(main_string, sub_string):
    # Initialize variables to store the start and end indices of the substring
    start = 0
    end = 0
    
    # Loop through the main string to find all occurrences of the substring
    while end < len(main_string):
        # Find the next occurrence of the substring starting from the current end index
        end = main_string.find(sub_string, end)
        
        # If the substring is found, update the start index to the current end index
        if end != -1:
            start = end + 1
        else:
            break
    
    # Return the substring and its start and end indices
    return (sub_string, start, end)
