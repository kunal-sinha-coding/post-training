def first_repeated_char(s):
    # Create a dictionary to store the frequency of each character
    char_count = {}
    
    # Iterate through each character in the string
    for char in s:
        # If the character is already in the dictionary, return it
        if char in char_count:
            return char
        # If the character is not in the dictionary, add it with a count of 1
        else:
            char_count[char] = 1
    
    # If no repeated character is found, return None
    return None