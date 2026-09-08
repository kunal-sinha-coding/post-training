def count_char_position(s):
    # Initialize a counter for characters at the same position in the alphabet
    count = 0
    # Iterate through each character in the string
    for i in range(len(s)):
        # Check if the character is at the same position in the alphabet
        if ord(s[i]) == ord('a') + i:
            count += 1
    return count
