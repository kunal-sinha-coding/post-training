def max_run_uppercase(s):
    # Initialize a counter for the maximum run of uppercase characters
    max_run = 0
    # Initialize a variable to keep track of the current run
    current_run = 0
    # Iterate through each character in the string
    for char in s:
        # If the character is uppercase, increment the current run
        if char.isupper():
            current_run += 1
        # If the character is not uppercase, update the maximum run if the current run is greater
        else:
            max_run = max(max_run, current_run)
            # Reset the current run to 0
            current_run = 0
    # After the loop, check if there is a last run
    max_run = max(max_run, current_run)
    return max_run