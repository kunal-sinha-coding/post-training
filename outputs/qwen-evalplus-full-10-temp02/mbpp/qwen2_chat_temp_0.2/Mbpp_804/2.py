def is_product_even(numbers):
    """
    Check if the product of numbers in a list is even or not.
    
    Args:
    numbers (list): A list of integers.
    
    Returns:
    bool: True if the product is even, False otherwise.
    
    Examples:
    >>> is_product_even([1, 2, 3])
    False
    >>> is_product_even([2, 4, 6])
    True
    >>> is_product_even([1, 3, 5])
    False
    >>> is_product_even([2, 4, 6, 8])
    True
    """
    product = 1
    for num in numbers:
        product *= num
    return product % 2 == 0