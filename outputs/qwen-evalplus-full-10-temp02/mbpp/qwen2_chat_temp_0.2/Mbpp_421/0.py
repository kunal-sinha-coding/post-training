def concatenate_tuple(input_tuple):
    # Initialize an empty string to store the concatenated result
    result = ""
    # Iterate over each element in the input tuple
    for element in input_tuple:
        # Concatenate the element with the delimiter
        result += element + "-"
    # Return the concatenated result
    return result[:-1]  # Remove the trailing delimiter
