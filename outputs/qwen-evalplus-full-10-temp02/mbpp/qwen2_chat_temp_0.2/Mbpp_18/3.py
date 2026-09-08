def remove_dirty_chars(s1, s2):
    # Initialize an empty string to store the result
    result = ""
    # Iterate through each character in the first string
    for char in s1:
        # Check if the character is not present in the second string
        if char not in s2:
            # Append the character to the result string
            result += char
    # Return the result string
    return result