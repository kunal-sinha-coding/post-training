def find_Rotations(s):
    # Initialize the minimum rotations needed
    min_rotations = 0
    
    # Iterate through the string to find the longest suffix that matches the prefix
    for i in range(len(s)):
        if s[i:] == s[:i]:
            # Increment the minimum rotations needed
            min_rotations += 1
    
    return min_rotations
