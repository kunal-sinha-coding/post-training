import math

def multiply_num(numbers):
    """
    Multiply all the numbers in the list and divide with the length of the list.
    
    Args:
    numbers (list): A list of numbers.
    
    Returns:
    float: The result of multiplying all numbers in the list and dividing by the length of the list.
    """
    return sum(numbers) / len(numbers)
