def remove_lowercase(input_string):
    # Initialize an empty string to store the result
    result = ""
    # Iterate through each character in the input string
    for char in input_string:
        # Check if the character is not a lowercase letter
        if char.isupper():
            # If it is, append it to the result string
            result += char
    # Return the result string with all lowercase letters removed
    return result