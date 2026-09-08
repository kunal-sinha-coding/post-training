def len_log(words):
    # Initialize a variable to keep track of the maximum length
    max_length = 0
    # Iterate through each word in the list
    for word in words:
        # Check if the current word is longer than the maximum length found so far
        if len(word) > max_length:
            # Update the maximum length if the current word is longer
            max_length = len(word)
    # Return the maximum length found
    return max_length