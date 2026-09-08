def count_occurance(text):
    # Initialize a counter to zero
    count = 0
    # Iterate through each character in the text
    for char in text:
        # Check if the character is 'std'
        if char == 'std':
            # Increment the counter
            count += 1
    # Return the total count of 'std'
    return count