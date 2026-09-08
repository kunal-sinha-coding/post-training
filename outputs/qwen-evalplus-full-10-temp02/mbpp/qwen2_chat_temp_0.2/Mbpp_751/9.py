def check_min_heap(arr):
    # Check if the array is empty
    if not arr:
        return False
    
    # Find the index of the first element
    index = 0
    
    # Iterate through the array starting from the second element
    for i in range(1, len(arr)):
        # If the current element is less than the element at the index of the previous element
        if arr[i] < arr[index]:
            return False
    
    # If all elements are in the correct order, return True
    return True