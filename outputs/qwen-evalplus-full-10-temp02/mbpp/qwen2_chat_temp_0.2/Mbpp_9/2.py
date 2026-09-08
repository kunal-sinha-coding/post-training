def find_Rotations(s):
    """
    Find the minimum number of rotations required to get the same string.
    
    Args:
    s (str): The input string.
    
    Returns:
    int: The minimum number of rotations required.
    """
    # Initialize the minimum rotation count to a large number
    min_rotations = float('inf')
    
    # Iterate through the string to find the longest suffix that matches the prefix
    for i in range(len(s)):
        # Check if the substring from the start to i is a prefix of the string
        if s[:i] == s[i:]:
            # Calculate the number of rotations needed to match the prefix
            rotations = len(s) - i
            # Update the minimum rotation count if the current rotation is smaller
            if rotations < min_rotations:
                min_rotations = rotations
    
    return min_rotations