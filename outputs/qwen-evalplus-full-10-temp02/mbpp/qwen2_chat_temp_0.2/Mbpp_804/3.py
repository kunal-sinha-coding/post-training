def is_product_even(numbers):
    """
    Check if the product of numbers in a list is even or not.
    
    Args:
    numbers (list): A list of integers.
    
    Returns:
    bool: True if the product of the numbers is even, False otherwise.
    """
    product = 1
    for num in numbers:
        product *= num
    return product % 2 == 0