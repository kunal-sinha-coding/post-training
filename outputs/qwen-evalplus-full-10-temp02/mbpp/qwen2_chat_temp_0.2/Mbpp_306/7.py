def max_sum_increasing_subseq(arr, n, k, m):
    # Initialize the DP array with the first element of the array
    dp = [arr[0]]
    
    # Iterate through the array starting from the second element
    for i in range(1, n):
        # Update the DP array with the maximum sum of increasing subsequence ending at the current element
        dp.append(max(dp[-1], dp[i] + arr[i]))
    
    # Return the maximum sum of increasing subsequence ending at the kth element
    return dp[k]
