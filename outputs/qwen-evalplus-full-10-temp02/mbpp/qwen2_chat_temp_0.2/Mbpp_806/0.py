def max_run_uppercase(s):
    # Initialize the maximum run to 0
    max_run = 0
    # Initialize the current run to 1
    current_run = 1
    
    # Iterate through the string
    for i in range(1, len(s)):
        # Check if the current character is uppercase
        if s[i].isupper():
            # Increment the current run
            current_run += 1
            # Update the maximum run if the current run is greater
            if current_run > max_run:
                max_run = current_run
        else:
            # Reset the current run to 1
            current_run = 1
    
    # Return the maximum run found
    return max_run