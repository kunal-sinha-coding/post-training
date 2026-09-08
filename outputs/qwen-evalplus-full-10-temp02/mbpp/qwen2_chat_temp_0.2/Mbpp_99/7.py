def decimal_to_binary(decimal_number):
    """
    Convert a given decimal number to its binary equivalent, represented as a string with no leading zeros.
    
    Parameters:
    decimal_number (int): The decimal number to be converted.
    
    Returns:
    str: The binary representation of the decimal number as a string.
    """
    # Convert the decimal number to binary using the built-in bin function
    binary_representation = bin(decimal_number)[2:]
    return binary_representation
