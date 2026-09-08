def max_sum_increasing_subseq(arr, n, k):
    # Initialize the dp array with the first element
    dp = [arr[0]]
    
    # Iterate through the array starting from the second element
    for i in range(1, n):
        # Update the dp array with the maximum sum of increasing subsequence ending at the current index
        dp.append(max(dp[-1], dp[i] + arr[i]))
    
    # Return the maximum sum of increasing subsequence ending at the kth index
    return dp[k]
