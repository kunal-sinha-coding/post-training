# Define the function to perform index-wise multiplication
def index_multiplication(tuple1, tuple2):
    # Initialize an empty list to store the result
    result = []
    # Iterate over the indices of the first tuple
    for index in range(len(tuple1)):
        # Multiply the corresponding elements from the two tuples
        result.append((tuple1[index][0] * tuple2[index][0], tuple1[index][1] * tuple2[index][1]))
    # Return the result list
    return result
