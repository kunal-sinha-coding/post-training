def get_Inv_Count(arr):
    # Initialize the count of inversions
    inv_count = 0
    
    # Iterate through the array
    for i in range(len(arr)):
        # Iterate through the array again to compare elements
        for j in range(i + 1, len(arr)):
            # Check if the elements at i and j are in the wrong order
            if arr[i] > arr[j]:
                # Increment the inversion count
                inv_count += 1
    
    # Return the total number of inversions
    return inv_count