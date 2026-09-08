def toggle_string(s):
    # Initialize an empty string to store the toggled characters
    toggled = ""
    # Iterate through each character in the input string
    for char in s:
        # Check if the character is uppercase
        if char.isupper():
            # Convert the character to lowercase
            toggled += char.lower()
        # If the character is lowercase
        elif char.islower():
            # Convert the character to uppercase
            toggled += char.upper()
        else:
            # If the character is neither uppercase nor lowercase, leave it unchanged
            toggled += char
    # Return the toggled string
    return toggled