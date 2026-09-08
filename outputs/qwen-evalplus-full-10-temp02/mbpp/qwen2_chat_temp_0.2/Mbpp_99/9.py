def decimal_to_binary(decimal_number):
    """
    Convert a given decimal number to its binary equivalent, represented as a string with no leading zeros.
    
    Args:
    decimal_number (int): The decimal number to be converted.
    
    Returns:
    str: The binary representation of the decimal number, with no leading zeros.
    """
    # Convert the decimal number to binary using the built-in bin function
    binary_representation = bin(decimal_number)[2:]  # [2:] to remove the '0b' prefix
    return binary_representation
