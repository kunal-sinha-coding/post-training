def odd_Equivalent(binary_str, n):
    # Initialize the count of numbers with an odd value
    count = 0
    
    # Iterate through the binary string
    for i in range(n):
        # Rotate the string by one position
        rotated_str = binary_str[1:] + binary_str[0]
        
        # Check if the rotated string has an odd number of '1's
        if rotated_str.count('1') % 2 != 0:
            count += 1
    
    return count
