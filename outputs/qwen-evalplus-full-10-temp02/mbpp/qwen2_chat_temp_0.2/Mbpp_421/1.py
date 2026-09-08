def concatenate_tuple(tup):
    # Initialize an empty string to store the concatenated result
    result = ""
    # Iterate over each element in the tuple
    for element in tup:
        # Concatenate the element with the delimiter
        result += element + "-"
    # Remove the trailing delimiter and return the result
    return result[:-1]
