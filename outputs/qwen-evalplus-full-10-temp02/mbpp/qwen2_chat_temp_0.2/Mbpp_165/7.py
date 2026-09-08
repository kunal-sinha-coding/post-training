def count_char_position(s):
    # Convert the string to lowercase to make the function case-insensitive
    s = s.lower()
    # Initialize a counter for characters at the same position in the alphabet
    count = 0
    # Iterate through each character in the string
    for i in range(len(s)):
        # Check if the character is at the same position in the alphabet
        if i == ord(s[i]) - ord('a'):
            # Increment the counter if it is
            count += 1
    # Return the total count of characters at the same position
    return count