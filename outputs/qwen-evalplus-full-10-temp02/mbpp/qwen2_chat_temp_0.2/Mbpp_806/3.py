def max_run_uppercase(s):
    # Initialize variables to keep track of the maximum run and the current run length
    max_run = 0
    current_run = 0
    
    # Iterate through each character in the string
    for char in s:
        # If the character is uppercase, increment the current run length
        if char.isupper():
            current_run += 1
        # If the character is not uppercase, update the maximum run if the current run is greater
        else:
            max_run = max(max_run, current_run)
            # Reset the current run length to 0
            current_run = 0
    
    # After the loop, check the last run
    max_run = max(max_run, current_run)
    
    return max_run