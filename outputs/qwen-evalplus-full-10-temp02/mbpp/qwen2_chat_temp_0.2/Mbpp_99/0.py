def decimal_to_binary(decimal_number):
    """
    Convert a given decimal number to its binary equivalent, represented as a string with no leading zeros.
    
    Args:
    decimal_number (int): The decimal number to be converted.
    
    Returns:
    str: The binary equivalent of the given decimal number.
    
    Examples:
    >>> decimal_to_binary(8)
    '1000'
    >>> decimal_to_binary(7)
    '111'
    >>> decimal_to_binary(15)
    '1111'
    """
    binary_number = ""
    while decimal_number > 0:
        remainder = decimal_number % 2
        binary_number = str(remainder) + binary_number
        decimal_number = decimal_number // 2
    return binary_number
