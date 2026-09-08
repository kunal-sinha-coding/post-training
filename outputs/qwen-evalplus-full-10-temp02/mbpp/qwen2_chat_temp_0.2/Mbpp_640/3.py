def remove_parenthesis(s):
    # Initialize an empty string to store the result
    result = ""
    # Iterate through each character in the input string
    for char in s:
        # Check if the character is not a parenthesis
        if char != '(':
            # Append the character to the result string
            result += char
    # Return the result string without the parenthesis
    return result