def concatenate_tuple(tup):
    # Initialize an empty string to store the concatenated result
    result = ''
    # Iterate over each element in the tuple
    for element in tup:
        # Append the element to the result string, followed by the delimiter
        result += element + delimiter
    # Return the concatenated string
    return result