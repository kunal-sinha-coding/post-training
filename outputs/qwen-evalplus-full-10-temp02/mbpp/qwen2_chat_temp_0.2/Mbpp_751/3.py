def check_min_heap(arr):
    # Check if the array is empty
    if not arr:
        return True
    
    # Find the index of the smallest element
    min_index = arr.index(min(arr))
    
    # Check if the smallest element is at the root of the heap
    if min_index == 0:
        return True
    
    # Check if the smallest element is greater than its parent
    for i in range(1, min_index):
        if arr[i] < arr[i - 1]:
            return False
    
    return True