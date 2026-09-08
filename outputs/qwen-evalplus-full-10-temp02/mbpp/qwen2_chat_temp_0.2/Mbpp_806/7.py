def max_run_uppercase(s):
    # Initialize the maximum run length to 0
    max_run = 0
    # Initialize the current run length to 1
    current_run = 1
    
    # Iterate through the string starting from the second character
    for i in range(1, len(s)):
        # If the current character is uppercase and the previous character is not
        if s[i].isupper() and s[i-1].islower():
            # Increment the current run length
            current_run += 1
        # If the current character is lowercase and the previous character is uppercase
        elif s[i].islower() and s[i-1].isupper():
            # Reset the current run length to 1
            current_run = 1
        # Update the maximum run length if the current run length is greater
        max_run = max(max_run, current_run)
    
    # Return the maximum run length found
    return max_run