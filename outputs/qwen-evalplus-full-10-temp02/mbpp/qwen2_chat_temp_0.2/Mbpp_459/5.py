def remove_uppercase(input_string):
    # Initialize an empty string to store the result
    result = ''
    # Iterate through each character in the input string
    for char in input_string:
        # Check if the character is not uppercase
        if char.islower():
            # Append the character to the result string
            result += char
    # Return the result string with all uppercase substrings removed
    return result