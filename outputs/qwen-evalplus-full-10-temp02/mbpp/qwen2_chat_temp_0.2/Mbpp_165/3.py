def count_char_position(s):
    # Convert the string to lowercase to make the function case-insensitive
    s = s.lower()
    # Initialize a counter for characters at the same position in the alphabet
    count = 0
    # Iterate over each character in the string
    for i in range(len(s)):
        # Check if the character at the current position is the same as the character at the same position in the alphabet
        if s[i] == s[i].lower():
            count += 1
    # Return the count of characters at the same position in the alphabet
    return count