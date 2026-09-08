def find_length(binary_string):
    # Initialize variables to store the maximum difference and the current count of 0s
    max_diff = 0
    current_count = 0
    
    # Iterate through each character in the binary string
    for char in binary_string:
        # If the character is 0, increment the current count
        if char == '0':
            current_count += 1
        # If the character is 1, reset the current count
        else:
            current_count = 0
        
        # Update the maximum difference if the current count is greater
        max_diff = max(max_diff, current_count)
    
    # Return the maximum difference found
    return max_diff