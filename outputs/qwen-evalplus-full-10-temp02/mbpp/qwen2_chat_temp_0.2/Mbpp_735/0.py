def toggle_middle_bits(n):
    # Extract the first and last bits of the number
    first_bit = n & 1
    last_bit = n >> 1 & 1
    
    # Toggle the bits
    toggled_first_bit = first_bit ^ 1
    toggled_last_bit = last_bit ^ 1
    
    # Combine the toggled bits
    result = toggled_first_bit << 1 | toggled_last_bit
    
    return result