def check_min_heap(arr):
    # Check if the array is empty
    if not arr:
        return True
    
    # Find the index of the first element
    root_index = 0
    
    # Traverse the array from the root to the end
    for i in range(1, len(arr)):
        # If the current element is smaller than the parent, return False
        if arr[i] < arr[root_index]:
            return False
        
        # Move the parent to the current index
        root_index = i
    
    # If all elements are in the correct order, return True
    return True