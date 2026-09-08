def sum_Of_Subarray_Prod(arr):
    # Initialize the result with the first element of the array
    res = arr[0]
    # Iterate through the array starting from the second element
    for i in range(1, len(arr)):
        # Multiply the current element with the result and add it to the result
        res *= arr[i]
        # Update the result with the maximum value between the current result and the updated result
        res = max(res, res)
    return res