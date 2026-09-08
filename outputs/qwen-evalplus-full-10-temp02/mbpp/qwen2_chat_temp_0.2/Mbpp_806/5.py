def max_run_uppercase(s):
    # Initialize the maximum run to 0
    max_run = 0
    # Initialize the current run to 1
    current_run = 1
    # Iterate through each character in the string
    for i in range(1, len(s)):
        # If the current character is uppercase and the previous character is not, update the current run
        if s[i].isupper() and s[i-1].islower():
            current_run += 1
        # Update the maximum run if the current run is greater
        else:
            max_run = max(max_run, current_run)
            # Reset the current run
            current_run = 1
    # Update the maximum run if the last character is uppercase
    max_run = max(max_run, current_run)
    return max_run