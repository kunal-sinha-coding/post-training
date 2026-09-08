def toggle_middle_bits(n):
    # Extract the first and last bits
    first_bit = n & 1
    last_bit = n >> 1
    
    # Toggle the bits
    toggled = first_bit ^ last_bit
    
    # Return the modified number
    return toggled