def check_greater(arr, n):
    # Iterate through the array and check if each element is greater than the first element
    for i in range(1, n):
        if arr[i] > arr[0]:
            return True
    # If no element is greater than the first element, return False
    return False