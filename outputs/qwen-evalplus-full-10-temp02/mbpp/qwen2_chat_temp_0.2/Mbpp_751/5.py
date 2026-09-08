def check_min_heap(arr):
    # Check if the array is empty
    if not arr:
        return True
    
    # Find the index of the first element
    root = 0
    
    # Traverse the array from the root to the end
    for i in range(1, len(arr)):
        # If the current element is greater than the root, return False
        if arr[root] > arr[i]:
            return False
        
        # Move the root to the current index
        root = i
    
    # If all elements are in the correct order, return True
    return True