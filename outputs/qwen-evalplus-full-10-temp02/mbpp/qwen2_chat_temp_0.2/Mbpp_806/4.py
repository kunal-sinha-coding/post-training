def max_run_uppercase(s):
    # Initialize the maximum run to 0
    max_run = 0
    # Iterate through the string
    for i in range(len(s)):
        # Check if the current character is uppercase
        if s[i].isupper():
            # Increment the maximum run if the current character is uppercase
            max_run += 1
    # Return the maximum run found
    return max_run