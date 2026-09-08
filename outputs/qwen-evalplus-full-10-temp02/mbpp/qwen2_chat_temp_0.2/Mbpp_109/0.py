def odd_Equivalent(binary_str, n):
    # Initialize the count of numbers with odd value
    count = 0
    
    # Iterate through the binary string
    for i in range(n):
        # Rotate the binary string by n positions
        rotated = binary_str[i:] + binary_str[:i]
        
        # Check if the rotated string has an odd number of '1's
        if rotated.count('1') % 2 != 0:
            count += 1
    
    return count