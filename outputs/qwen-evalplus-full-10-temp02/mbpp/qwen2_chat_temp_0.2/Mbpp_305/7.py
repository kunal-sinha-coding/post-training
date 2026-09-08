def start_withp(words):
    # Initialize two empty strings to store the words starting with 'p'
    result1 = ""
    result2 = ""
    
    # Iterate through each word in the list
    for word in words:
        # Check if the word starts with 'p'
        if word.startswith('p'):
            # If it does, append it to the result1 string
            result1 += word
        # Check if the word starts with 'P'
        elif word.startswith('P'):
            # If it does, append it to the result2 string
            result2 += word
    
    # Return the two words
    return result1, result2