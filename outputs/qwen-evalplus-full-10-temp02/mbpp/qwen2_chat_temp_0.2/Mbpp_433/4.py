def check_greater(arr, n):
    # Iterate through the array and check if each element is greater than the given number
    for i in range(n):
        if arr[i] > n:
            return True
    # If no element is greater than the given number, return False
    return False