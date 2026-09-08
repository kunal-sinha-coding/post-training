def kth_element(arr, k):
    # Ensure k is within the bounds of the array
    if k < 1 or k > len(arr):
        return None
    # Return the element at the k-th index
    return arr[k - 1]