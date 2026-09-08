def decimal_to_binary(number):
    """
    Convert a given decimal number to its binary equivalent, represented as a string with no leading zeros.
    
    Args:
    number (int): The decimal number to convert.
    
    Returns:
    str: The binary representation of the given decimal number.
    """
    # Convert the decimal number to binary using the built-in bin function
    binary_representation = bin(number)[2:]  # [2:] removes the '0b' prefix
    return binary_representation
