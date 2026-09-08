def concatenate_tuple(test_tuple):
    # Initialize an empty string to store the concatenated result
    result = ''
    # Iterate over each element in the tuple
    for element in test_tuple:
        # Concatenate the element with the delimiter
        result += element + '-'
    # Return the concatenated string
    return result[:-1]  # Remove the trailing delimiter
