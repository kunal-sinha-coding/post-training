def is_product_even(numbers):
    """
    Check if the product of numbers in the list is even or not.
    
    Args:
    numbers (list): A list of integers.
    
    Returns:
    bool: True if the product is even, False otherwise.
    """
    product = 1
    for num in numbers:
        product *= num
    return product % 2 == 0