def toggle_middle_bits(number):
    # Extract the first and last bits of the number
    first_bit = number & 1
    last_bit = number >> 1
    
    # Toggle the bits
    toggled_number = first_bit ^ last_bit
    
    return toggled_number