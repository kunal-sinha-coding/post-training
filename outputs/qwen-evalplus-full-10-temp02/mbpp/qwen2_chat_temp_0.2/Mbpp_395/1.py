def first_non_repeating_character(s):
    # Create a dictionary to count occurrences of each character
    char_count = {}
    
    # Count the occurrences of each character in the string
    for char in s:
        if char in char_count:
            char_count[char] += 1
        else:
            char_count[char] = 1
    
    # Iterate through the string again to find the first non-repeating character
    for char in s:
        if char_count[char] == 1:
            return char
    
    # If no non-repeating character is found, return None
    return None