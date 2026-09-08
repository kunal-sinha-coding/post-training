def find_Rotations(s):
    # Initialize the minimum rotation count to a large number
    min_rotation = float('inf')
    
    # Iterate through the string to find the minimum rotation count
    for i in range(len(s)):
        # Check if the substring from the current position to the end is equal to the substring from the start to the current position
        if s[i:] == s[:i]:
            # Calculate the number of rotations needed
            rotation_count = len(s) - i
            # Update the minimum rotation count if the current rotation count is smaller
            if rotation_count < min_rotation:
                min_rotation = rotation_count
    
    return min_rotation