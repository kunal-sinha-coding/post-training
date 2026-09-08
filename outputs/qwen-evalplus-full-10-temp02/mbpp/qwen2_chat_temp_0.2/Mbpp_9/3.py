def find_Rotations(s):
    # Initialize the minimum rotations needed to make the string equal to its reverse
    rotations = 0
    # Iterate through the string to find the first non-reverse character
    for i in range(len(s)):
        # If the character is not equal to its reverse, increment the rotations
        if s[i] != s[-(i+1)]:
            rotations += 1
    return rotations