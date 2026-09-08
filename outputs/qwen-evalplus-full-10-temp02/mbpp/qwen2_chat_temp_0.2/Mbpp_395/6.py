def first_non_repeating_character(s):
    # Create a dictionary to count occurrences of each character
    char_count = {}
    # Iterate through each character in the string
    for char in s:
        # If the character is already in the dictionary, increment its count
        if char in char_count:
            char_count[char] += 1
        # If the character is not in the dictionary, add it with a count of 1
        else:
            char_count[char] = 1
    # Iterate through the dictionary to find the first character with a count of 1
    for char in s:
        if char_count[char] == 1:
            return char
    # If no non-repeating character is found, return None
    return None