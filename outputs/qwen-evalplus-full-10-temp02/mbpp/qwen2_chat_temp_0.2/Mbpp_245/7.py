def max_sum(arr):
    # Initialize variables to store the maximum sum of a bitonic subsequence
    max_sum = 0
    # Iterate through the array to find the maximum sum of a bitonic subsequence
    for i in range(len(arr)):
        # Initialize the maximum sum of a bitonic subsequence ending at index i
        max_ending_here = 0
        # Iterate through the subarray starting from index i
        for j in range(i):
            # Update the maximum sum of a bitonic subsequence ending at index j
            max_ending_here = max(max_ending_here, arr[j])
        # Update the maximum sum of a bitonic subsequence ending at index i
        max_sum = max(max_sum, max_ending_here + arr[i])
    return max_sum