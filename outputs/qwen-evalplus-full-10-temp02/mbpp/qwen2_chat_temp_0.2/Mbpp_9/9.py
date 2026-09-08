def find_Rotations(s):
    # Initialize the minimum rotation count to a large number
    min_rotation = float('inf')
    
    # Iterate through the string to find the minimum rotation count
    for i in range(len(s)):
        # Check if the substring from the start to the current index is equal to the substring from the end to the current index
        if s[i:] == s[-i:]:
            # Calculate the rotation count by subtracting the length of the substring from the length of the original string
            rotation = len(s) - i
            # Update the minimum rotation count if the current rotation count is smaller
            if rotation < min_rotation:
                min_rotation = rotation
    
    # Return the minimum rotation count
    return min_rotation