def search(arr):
    # Initialize a variable to store the result
    result = arr[0]
    # Iterate through the array starting from the second element
    for i in range(1, len(arr)):
        # Check if the current element is not equal to the result
        if arr[i] != result:
            # Update the result to the current element
            result = arr[i]
    # Return the result
    return result