def count_char_position(s):
    # Initialize a counter for characters at the same position in the alphabet
    count = 0
    # Iterate through each character in the string
    for i in range(len(s)):
        # Check if the character at the current position is the same as the character at the same position in the alphabet
        if s[i] == s[i].lower():
            count += 1
    # Return the total count of such characters
    return count