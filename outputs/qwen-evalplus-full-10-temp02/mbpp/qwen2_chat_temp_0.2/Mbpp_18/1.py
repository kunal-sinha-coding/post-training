# Define the function to remove characters from the first string that are present in the second string
def remove_dirty_chars(str1, str2):
    # Initialize an empty string to store the result
    result = ""
    # Iterate through each character in the first string
    for char in str1:
        # Check if the character is present in the second string
        if char not in str2:
            # If not, append it to the result string
            result += char
    # Return the result string
    return result