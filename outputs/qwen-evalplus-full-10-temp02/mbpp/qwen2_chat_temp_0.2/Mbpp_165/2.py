def count_char_position(s):
    """
    Count the number of characters in a string that occur at the same position in the string as in the English alphabet (case insensitive).
    
    Parameters:
    s (str): The input string to be analyzed.
    
    Returns:
    int: The count of characters at the same position in the English alphabet.
    """
    # Define the English alphabet
    alphabet = "abcdefghijklmnopqrstuvwxyz"
    # Initialize a counter for characters at the same position
    count = 0
    # Iterate over each character in the string
    for i in range(len(s)):
        # Check if the character is at the same position in the alphabet
        if alphabet[i] == s[i].lower():
            count += 1
    return count
