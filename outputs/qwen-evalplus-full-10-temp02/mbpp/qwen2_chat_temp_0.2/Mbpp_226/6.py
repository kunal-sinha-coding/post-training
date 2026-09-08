def odd_values_string(input_string):
    # Initialize an empty string to store the result
    result = ''
    # Iterate over the input string
    for i in range(len(input_string)):
        # Check if the index is odd
        if i % 2 != 0:
            # Append the character to the result string
            result += input_string[i]
    # Return the result string
    return result