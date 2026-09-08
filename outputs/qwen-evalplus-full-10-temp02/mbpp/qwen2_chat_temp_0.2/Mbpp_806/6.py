def max_run_uppercase(s):
    # Initialize the maximum run length to 0
    max_length = 0
    # Initialize the current run length to 1
    current_run = 1
    
    # Iterate through each character in the string
    for i in range(1, len(s)):
        # If the current character is uppercase and the previous character is not uppercase, update the current run length
        if s[i].isupper() and s[i-1].islower():
            current_run += 1
        # If the current character is uppercase and the previous character is uppercase, update the maximum run length
        elif s[i].isupper() and s[i-1].isupper():
            max_length = max(max_length, current_run)
            # Reset the current run length to 1
            current_run = 1
    
    # Return the maximum run length found
    return max_length