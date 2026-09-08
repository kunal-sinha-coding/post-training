def concatenate_tuple(test_tup):
    # Initialize an empty string to store the concatenated result
    result = ""
    # Iterate over each element in the tuple
    for element in test_tup:
        # Concatenate the current element with the delimiter
        result += element + "-"
    # Return the concatenated result
    return result[:-1]
