def get_Char(s):
    # Initialize the result string with the first character of the input string
    result = s[0]
    
    # Iterate through each character in the string
    for char in s:
        # Calculate the ASCII value of the current character
        ascii_value = ord(char)
        
        # Add the ASCII value to the result string modulo 26
        result = chr((ascii_value + result) % 26)
    
    # Return the final result string
    return result