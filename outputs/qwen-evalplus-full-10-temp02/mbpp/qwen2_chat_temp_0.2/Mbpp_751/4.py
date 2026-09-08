def check_min_heap(arr):
    # Check if the array is empty
    if not arr:
        return False
    
    # Find the index of the last element
    last_index = len(arr) - 1
    
    # Check if the last element is greater than its parent
    if arr[last_index] > arr[(last_index - 1) // 2]:
        return False
    
    # Check if the parent is greater than its children
    for i in range(last_index // 2, 0, -1):
        if arr[i] > arr[(i - 1) // 2]:
            return False
    
    return True