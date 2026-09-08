def check_min_heap(arr):
    # Check if the array is empty
    if not arr:
        return True
    
    # Find the index of the first element
    root_index = 0
    
    # Iterate through the array starting from the second element
    for i in range(1, len(arr)):
        # If the current element is smaller than the root element, return False
        if arr[i] < arr[root_index]:
            return False
        
        # Move the root element to the current index
        root_index = i
    
    # If all elements are in the correct order, return True
    return True