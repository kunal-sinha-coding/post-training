def get_Inv_Count(arr):
    # Initialize the count of inversions
    inv_count = 0
    
    # Iterate through the array
    for i in range(len(arr)):
        # Compare each element with its adjacent elements
        for j in range(i + 1, len(arr)):
            # If the current element is greater than the adjacent element, increment the inversion count
            if arr[i] > arr[j]:
                inv_count += 1
    
    # Return the total count of inversions
    return inv_count