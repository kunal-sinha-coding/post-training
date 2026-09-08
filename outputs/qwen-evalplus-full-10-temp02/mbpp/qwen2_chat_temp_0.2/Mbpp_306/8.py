def max_sum_increasing_subseq(arr, n, k, m):
    # Initialize the dp array with -1
    dp = [-1] * (n + 1)
    
    # Base case: if k is greater than n, return 0
    if k > n:
        return 0
    
    # Initialize the result with the first element of the array
    result = arr[0]
    
    # Iterate through the array starting from the second element
    for i in range(1, n + 1):
        # Find the maximum value in the subarray ending at i
        max_value = max(dp[i - 1], arr[i - 1])
        
        # Update the result with the maximum value found so far
        result = max(result, max_value + arr[i])
    
    return result