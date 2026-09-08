def find_Rotations(s):
    # Initialize the minimum rotations needed
    rotations_needed = 0
    # Iterate through the string to find the longest suffix
    for i in range(len(s)):
        # Check if the suffix is the same as the prefix
        if s[i:] == s[:i]:
            # Increment the rotations needed
            rotations_needed += 1
    return rotations_needed