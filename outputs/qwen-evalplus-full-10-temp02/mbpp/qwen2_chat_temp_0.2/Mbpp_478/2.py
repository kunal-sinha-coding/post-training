def remove_lowercase(input_string):
    # Initialize an empty string to store the result
    result = ""
    # Iterate through each character in the input string
    for char in input_string:
        # Check if the character is not lowercase
        if char.islower():
            # If not, append it to the result string
            result += char
    # Return the result string with all lowercase substrings removed
    return result