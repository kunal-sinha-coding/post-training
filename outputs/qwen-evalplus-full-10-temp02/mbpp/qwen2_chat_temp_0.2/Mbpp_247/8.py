def lps(s):
    n = len(s)
    # Create a 2D array to store the lengths of longest palindromic subsequences
    dp = [[0] * n for _ in range(n)]
    
    # Fill the dp array
    for i in range(n):
        for j in range(i, n):
            if s[i] == s[j]:
                dp[i][j] = 1 + dp[i + 1][j - 1]
            else:
                dp[i][j] = max(dp[i + 1][j], dp[i][j - 1])
    
    # The length of the longest palindromic subsequence is in the bottom-right corner of the dp array
    return dp[0][n - 1]