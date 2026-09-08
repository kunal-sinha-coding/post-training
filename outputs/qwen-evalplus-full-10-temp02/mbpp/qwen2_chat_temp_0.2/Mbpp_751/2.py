def check_min_heap(arr):
    # Check if the array is empty
    if not arr:
        return False
    
    # Find the index of the first element
    root_index = 0
    
    # Traverse the array to find the index of the largest element
    for i in range(1, len(arr)):
        if arr[root_index] < arr[i]:
            root_index = i
    
    # Check if the largest element is at the root index
    if arr[root_index] > arr[len(arr) - 1]:
        return False
    
    # Check if the array is a min heap
    for i in range(len(arr)):
        # Check if the current element is greater than its parent
        if arr[i] > arr[(i - 1) // 2]:
            return False
    
    return True