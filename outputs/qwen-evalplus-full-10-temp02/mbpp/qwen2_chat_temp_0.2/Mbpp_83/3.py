def get_Char(s):
    # Initialize the result string with the first character of the input string
    result = s[0]
    
    # Iterate through each character in the input string
    for i in range(1, len(s)):
        # Calculate the ASCII value of the current character
        ascii_value = ord(s[i])
        
        # Add the ASCII value to the result string modulo 26
        result = chr((ascii_value + result) % 26)
    
    return result