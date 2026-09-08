def find_length(binary_string):
    # Initialize variables to keep track of the maximum difference and the current count of 0s
    max_diff = 0
    current_count = 0
    
    # Iterate through each character in the binary string
    for char in binary_string:
        # If the character is '0', increment the current count
        if char == '0':
            current_count += 1
        # If the character is '1', update the maximum difference if the current count is greater
        else:
            max_diff = max(max_diff, current_count)
            # Reset the current count to 0
            current_count = 0
    
    # After the loop, check the last sub-string
    max_diff = max(max_diff, current_count)
    
    return max_diff