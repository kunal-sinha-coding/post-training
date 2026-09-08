def lps(s):
    # Initialize a 2D list to store the lengths of longest palindromic subsequences
    dp = [[0] * len(s) for _ in range(len(s))]
    
    # Fill the dp table
    for i in range(1, len(s)):
        for j in range(i):
            if s[i] == s[j]:
                dp[i][j] = dp[i-1][j-1] + 2
            else:
                dp[i][j] = max(dp[i-1][j], dp[i][j-1])
    
    # The length of the longest palindromic subsequence is the value in the bottom-right corner of the dp table
    return dp[-1][-1]