def reverse_Array_Upto_K(arr, k):
    # Initialize pointers for the start and end of the array
    start = 0
    end = k - 1
    
    # Swap elements from start to end
    while start < end:
        arr[start], arr[end] = arr[end], arr[start]
        start += 1
        end -= 1
    
    return arr