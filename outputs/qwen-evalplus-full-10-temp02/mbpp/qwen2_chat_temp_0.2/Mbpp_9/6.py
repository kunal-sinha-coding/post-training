def find_Rotations(s):
    # Initialize the minimum rotations needed
    rotations = 0
    # Iterate through the string to find the longest suffix that is a prefix of the original string
    for i in range(len(s)):
        if s[i:] == s[:i]:
            rotations += 1
    return rotations
