def kth_element(arr, k):
    # Sort the array in ascending order
    arr.sort()
    # Return the kth element from the sorted array
    return arr[k-1]