def get_Char(s):
    # Initialize the result to an empty string
    result = ""
    # Iterate through each character in the string
    for char in s:
        # Add the ASCII value of the character to the result
        result += str(ord(char))
    # Return the result
    return result