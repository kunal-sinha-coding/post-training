def odd_Equivalent(binary_str, n):
    # Initialize the count of numbers with odd values
    count = 0
    
    # Iterate through the binary string
    for i in range(n):
        # Rotate the string by n positions
        rotated_str = binary_str[-n:] + binary_str[:-n]
        
        # Check if the rotated string has an odd number of '1's
        if rotated_str.count('1') % 2 != 0:
            count += 1
    
    return count