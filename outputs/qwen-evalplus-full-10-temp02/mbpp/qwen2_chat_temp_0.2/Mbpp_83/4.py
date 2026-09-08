def get_Char(s):
    # Initialize the result to an empty string
    result = ""
    # Iterate through each character in the string
    for char in s:
        # Calculate the ASCII value of the character
        ascii_value = ord(char)
        # Add the ASCII value to the result
        result += str(ascii_value % 26)
    # Return the result
    return result