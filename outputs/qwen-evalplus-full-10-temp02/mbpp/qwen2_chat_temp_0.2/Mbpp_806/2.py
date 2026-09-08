def max_run_uppercase(s):
    # Initialize the maximum run length to 0
    max_length = 0
    # Initialize the current run length to 1
    current_length = 1
    
    # Iterate through the string starting from the second character
    for i in range(1, len(s)):
        # If the current character is uppercase and the previous character is lowercase
        if s[i].isupper() and s[i-1].islower():
            # Increment the current run length
            current_length += 1
        # If the current character is uppercase and the previous character is not lowercase
        elif s[i].isupper() and not s[i-1].islower():
            # Update the maximum run length if the current run length is greater
            max_length = max(max_length, current_length)
            # Reset the current run length to 1
            current_length = 1
    
    # Update the maximum run length if the last character is uppercase
    max_length = max(max_length, current_length)
    
    return max_length