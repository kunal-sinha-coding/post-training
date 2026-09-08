def reverse_Array_Upto_K(arr, k):
    # Initialize two pointers, one starting from the beginning and the other from the end of the array
    left = 0
    right = len(arr) - 1
    
    # Continue the process until the left pointer is less than or equal to the right pointer
    while left <= right:
        # Swap the elements at the left and right pointers
        arr[left], arr[right] = arr[right], arr[left]
        # Move the left pointer one step to the right
        left += 1
        # Move the right pointer one step to the left
        right -= 1
    
    return arr