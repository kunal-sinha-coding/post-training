def find_Rotations(s):
    # Initialize the minimum rotation count to a large number
    min_rotations = float('inf')
    # Iterate through all possible rotations of the string
    for i in range(len(s)):
        # Rotate the string by slicing it into two parts
        rotated = s[i:] + s[:i]
        # Check if the rotated string is equal to the original string
        if rotated == s:
            # Update the minimum rotation count if the current rotation is smaller
            min_rotations = min(min_rotations, len(s) - i)
    # Return the minimum rotation count
    return min_rotations