def concatenate_tuple(input_tuple):
    # Initialize an empty string to store the concatenated result
    result = ""
    # Iterate over each element in the input tuple
    for element in input_tuple:
        # Concatenate each element to the result string with the delimiter
        result += element + "-"
    # Return the concatenated string
    return result[:-1]
