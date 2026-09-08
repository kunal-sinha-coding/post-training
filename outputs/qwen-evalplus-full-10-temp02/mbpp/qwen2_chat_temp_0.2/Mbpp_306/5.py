def max_sum_increasing_subseq(arr, n, k, m):
    # Initialize the DP array with the first element of the array
    dp = [arr[0]]
    
    # Iterate through the array starting from the second element
    for i in range(1, n):
        # Update the DP array with the maximum sum of increasing subsequence ending at the current index
        dp.append(max(dp[i-1], dp[i] + arr[i]))
    
    # Return the maximum sum of increasing subsequence ending at index k
    return dp[k]