def substract_elements(tuple1, tuple2):
    # Initialize an empty list to store the result
    result = []
    # Iterate over the indices of the tuples
    for i in range(len(tuple1)):
        # Subtract the element of tuple1 from the element of tuple2 at the same index
        result.append(tuple1[i] - tuple2[i])
    # Return the list of results
    return result