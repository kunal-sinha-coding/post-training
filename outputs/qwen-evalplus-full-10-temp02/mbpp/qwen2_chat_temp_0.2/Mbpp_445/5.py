def index_multiplication(tup1, tup2):
    # Initialize an empty list to store the result
    result = []
    # Iterate over the indices of the tuples
    for i in range(len(tup1)):
        # Multiply the corresponding elements from both tuples
        result.append((tup1[i][0] * tup2[i][0], tup1[i][1] * tup2[i][1]))
    # Return the result list
    return result