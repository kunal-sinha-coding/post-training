def find_adverb_position(sentence):
    # Split the sentence into words
    words = sentence.split()
    # Initialize variables to store the position of the first adverb and its value
    position = -1
    adverb = ""
    
    # Iterate through each word in the sentence
    for i, word in enumerate(words):
        # Check if the word is an adverb
        if word.startswith("ad"):
            # Update the position and adverb if the current word is the first adverb found
            if position == -1:
                position = i
                adverb = word
    
    # Return the position and adverb
    return position, adverb
