def find_Rotations(s):
    # Initialize the minimum rotations needed
    rotations_needed = 0
    # Iterate through the string to find the first non-repeating character
    for i in range(len(s)):
        if s[i] == s[(i + 1) % len(s)]:
            rotations_needed += 1
    return rotations_needed