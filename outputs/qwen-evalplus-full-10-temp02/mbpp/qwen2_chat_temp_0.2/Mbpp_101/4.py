def kth_element(arr, k):
    # Sort the array in ascending order
    arr.sort()
    # Return the kth element in the sorted array
    return arr[k-1]