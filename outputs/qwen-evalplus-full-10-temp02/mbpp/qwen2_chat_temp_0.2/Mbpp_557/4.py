def toggle_string(s):
    # Initialize an empty string to store the toggled characters
    result = ""
    # Iterate through each character in the input string
    for char in s:
        # Check if the character is uppercase
        if char.isupper():
            # Convert the character to lowercase and append to the result
            result += char.lower()
        # If the character is lowercase
        else:
            # Convert the character to uppercase and append to the result
            result += char.upper()
    # Return the toggled string
    return result