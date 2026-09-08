def check_greater(arr, n):
    # Iterate through each element in the array
    for i in range(n):
        # Check if the current element is greater than the first element
        if arr[i] > arr[0]:
            return True
    # If no element is greater than the first element, return False
    return False