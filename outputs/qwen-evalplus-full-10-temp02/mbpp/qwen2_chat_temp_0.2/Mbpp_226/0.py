def odd_values_string(s):
    # Initialize an empty string to store the result
    result = ''
    # Iterate through the string using a for loop
    for i in range(len(s)):
        # Check if the index is even
        if i % 2 == 0:
            # Append the character to the result string
            result += s[i]
    # Return the result string
    return result