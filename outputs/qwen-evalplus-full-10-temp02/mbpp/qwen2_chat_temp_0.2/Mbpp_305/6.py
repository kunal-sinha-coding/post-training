def start_withp(words):
    # Initialize two empty strings to store the words starting with 'p'
    word1 = ""
    word2 = ""
    
    # Iterate through each word in the list
    for word in words:
        # Check if the word starts with 'p'
        if word.startswith('p'):
            # If it does, assign the word to the appropriate string
            if word1 == "":
                word1 = word
            else:
                word2 = word
    
    # Return the two words
    return word1, word2