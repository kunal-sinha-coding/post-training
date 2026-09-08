# Define the function to remove odd characters from a string
def remove_odd(s):
    # Initialize an empty string to store the result
    result = ""
    # Iterate through each character in the input string
    for char in s:
        # Check if the character is odd
        if int(char) % 2 != 0:
            # If odd, append it to the result string
            result += char
    # Return the result string with odd characters removed
    return result
