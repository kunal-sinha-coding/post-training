def remove_lowercase(s):
    # Initialize an empty string to store the result
    result = ""
    # Iterate through each character in the input string
    for char in s:
        # Check if the character is not a lowercase letter
        if not char.islower():
            # Append the character to the result string
            result += char
    # Return the result string with all lowercase letters removed
    return result