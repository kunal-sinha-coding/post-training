def count_occurance(text):
    # Initialize a counter for the occurrences of 'std'
    count = 0
    # Iterate through each character in the text
    for char in text:
        # Check if the current character is 'std'
        if char == 'std':
            # Increment the counter if it is
            count += 1
    # Return the total count of 'std'
    return count