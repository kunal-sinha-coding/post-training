def decimal_to_binary(decimal_number):
    """
    Convert a given decimal number to its binary equivalent, represented as a string with no leading zeros.
    
    Args:
    decimal_number (int): The decimal number to be converted.
    
    Returns:
    str: The binary representation of the decimal number as a string.
    
    Examples:
    >>> decimal_to_binary(8)
    '1000'
    >>> decimal_to_binary(7)
    '111'
    >>> decimal_to_binary(0)
    '0'
    >>> decimal_to_binary(15)
    '1111'
    """
    binary_representation = ''
    while decimal_number > 0:
        remainder = decimal_number % 2
        binary_representation = str(remainder) + binary_representation
        decimal_number //= 2
    return binary_representation
