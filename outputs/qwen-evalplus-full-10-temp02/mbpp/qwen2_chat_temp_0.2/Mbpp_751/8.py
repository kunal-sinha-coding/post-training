def check_min_heap(arr):
    # Check if the array is empty
    if not arr:
        return True
    
    # Find the index of the first element
    index = 0
    
    # Traverse the array to find the minimum element
    for i in range(1, len(arr)):
        if arr[i] < arr[index]:
            index = i
    
    # Check if the first element is the minimum
    if arr[0] < arr[index]:
        return True
    
    # If no minimum element is found, the array is not a min heap
    return False