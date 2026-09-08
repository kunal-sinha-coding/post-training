def lps(s):
    n = len(s)
    dp = [[0] * (n + 1) for _ in range(n + 1)]
    
    # Build the dp table
    for i in range(1, n + 1):
        for j in range(1, n + 1):
            if s[i - 1] == s[j - 1]:
                dp[i][j] = dp[i - 1][j - 1] + 1
            else:
                dp[i][j] = max(dp[i - 1][j], dp[i][j - 1])
    
    # The length of the longest palindromic subsequence is the value in the bottom-right corner of the dp table
    return dp[n][n]
