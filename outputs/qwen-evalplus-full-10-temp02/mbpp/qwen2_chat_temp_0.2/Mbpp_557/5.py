def toggle_string(s):
    """
    Toggle the case of all characters in a string.
    
    Args:
    s (str): The input string to be toggled.
    
    Returns:
    str: The string with toggled case characters.
    """
    # Initialize an empty string to store the result
    result = ""
    # Iterate through each character in the input string
    for char in s:
        # Check if the character is uppercase
        if char.isupper():
            # Convert it to lowercase
            result += char.lower()
        # If the character is lowercase
        elif char.islower():
            # Convert it to uppercase
            result += char.upper()
        # If the character is neither uppercase nor lowercase, leave it unchanged
        else:
            result += char
    return result