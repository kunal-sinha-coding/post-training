def count_occurance(s):
    # Initialize a counter to zero
    count = 0
    # Iterate through each character in the string
    for char in s:
        # Check if the character is 'std'
        if char == 'std':
            # Increment the counter if it is
            count += 1
    # Return the total count of 'std'
    return count