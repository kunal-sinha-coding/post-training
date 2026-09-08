def toggle_string(s):
    # Initialize an empty string to store the result
    result = ""
    # Iterate through each character in the input string
    for char in s:
        # Check if the character is uppercase
        if char.isupper():
            # Convert the character to lowercase
            result += char.lower()
        # If the character is lowercase
        else:
            # Convert the character to uppercase
            result += char.upper()
    # Return the modified string
    return result