def first_repeated_char(s):
    # Create a dictionary to store the count of each character
    char_count = {}
    
    # Iterate through each character in the string
    for char in s:
        # If the character is already in the dictionary, it means it's repeated
        if char in char_count:
            return char
        # Otherwise, add the character to the dictionary with a count of 1
        else:
            char_count[char] = 1
    
    # If no repeated character is found, return None
    return None