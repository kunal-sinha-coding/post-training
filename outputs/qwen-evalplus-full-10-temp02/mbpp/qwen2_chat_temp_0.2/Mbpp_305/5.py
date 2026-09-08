def start_withp(words):
    # Initialize two empty strings to store words starting with 'p'
    result1 = ""
    result2 = ""
    
    # Iterate through each word in the list
    for word in words:
        # Check if the word starts with 'p'
        if word.startswith('p'):
            # If it does, append it to the first result string
            result1 += word
        else:
            # If it doesn't, append it to the second result string
            result2 += word
    
    # Return the two result strings
    return result1, result2
