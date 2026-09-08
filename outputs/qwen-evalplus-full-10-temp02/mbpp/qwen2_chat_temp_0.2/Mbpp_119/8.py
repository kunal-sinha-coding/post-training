def search(arr):
    # Initialize a variable to store the result
    result = arr[0]
    # Iterate through the array starting from the second element
    for i in range(1, len(arr)):
        # Check if the current element is different from the previous one
        if arr[i] != arr[i-1]:
            # Update the result to the current element
            result = arr[i]
    return result