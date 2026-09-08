def start_withp(words):
    # Initialize two empty strings to store the words starting with 'p'
    result1 = ""
    result2 = ""
    
    # Iterate through each word in the list
    for word in words:
        # Check if the word starts with 'p'
        if word.startswith('p'):
            # If it does, append the word to the appropriate result string
            if result1 == "":
                result1 = word
            else:
                result2 = word
    
    # Return the two words
    return result1, result2