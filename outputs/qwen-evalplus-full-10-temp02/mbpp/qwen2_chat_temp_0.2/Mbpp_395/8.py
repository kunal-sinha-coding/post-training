def first_non_repeating_character(s):
    # Create a dictionary to store the frequency of each character
    frequency = {}
    
    # Count the frequency of each character in the string
    for char in s:
        if char in frequency:
            frequency[char] += 1
        else:
            frequency[char] = 1
    
    # Iterate through the string again to find the first non-repeating character
    for char in s:
        if frequency[char] == 1:
            return char
    
    # If no non-repeating character is found, return None
    return None