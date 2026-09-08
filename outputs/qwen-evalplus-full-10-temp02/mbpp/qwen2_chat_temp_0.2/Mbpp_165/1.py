def count_char_position(s):
    """
    Count the number of characters in a string that occur at the same position in the string as in the English alphabet (case insensitive).
    
    Args:
    s (str): The input string.
    
    Returns:
    int: The count of characters at the same position in the English alphabet.
    """
    # Define the English alphabet
    alphabet = "abcdefghijklmnopqrstuvwxyz"
    # Initialize a counter for characters at the same position
    count = 0
    # Iterate through the string
    for i in range(len(s)):
        # Check if the character at the current position is in the alphabet
        if s[i] in alphabet:
            # Increment the counter if it is
            count += 1
    return count
