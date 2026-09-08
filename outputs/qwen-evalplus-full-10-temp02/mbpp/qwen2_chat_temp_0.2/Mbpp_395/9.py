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
    # Initialize a variable to store the first non-repeating character
    first_non_repeating = None
    # Iterate through each character in the string again
    for char in s:
        # If the character's count is 1 and it's not the first non-repeating character
        if char_count[char] == 1 and first_non_repeating is None:
            first_non_repeating = char
    # Return the first non-repeating character
    return first_non_repeating