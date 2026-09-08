def check_min_heap(arr):
    # Check if the array is empty
    if not arr:
        return False
    
    # Find the index of the largest element
    largest_index = arr.index(max(arr))
    
    # Check if the largest element is at the end of the array
    if largest_index == len(arr) - 1:
        return True
    
    # Check if the largest element is greater than its neighbors
    for i in range(largest_index - 1, largest_index + 2):
        if arr[i] > arr[i + 1] or arr[i] > arr[i - 1]:
            return False
    
    return True