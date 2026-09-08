def get_Inv_Count(arr):
    # Initialize the inversion count to 0
    inv_count = 0
    # Iterate through the array
    for i in range(len(arr)):
        # Iterate through the array again starting from the current index
        for j in range(i + 1, len(arr)):
            # Check if the elements at indices i and j are in the wrong order
            if arr[i] > arr[j]:
                # Increment the inversion count
                inv_count += 1
    # Return the total number of inversions
    return inv_count