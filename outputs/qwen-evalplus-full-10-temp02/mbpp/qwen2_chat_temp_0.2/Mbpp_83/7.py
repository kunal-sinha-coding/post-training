def get_Char(s):
    # Initialize the result variable to store the final character
    result = ''
    # Iterate through each character in the string
    for char in s:
        # Calculate the ASCII value of the character
        ascii_value = ord(char)
        # Add the ASCII value modulo 26 to the result
        result += str((ascii_value + 26) % 26)
    # Return the final result
    return result