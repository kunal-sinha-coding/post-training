def test_three_equal(a, b, c):
    """
    Count the number of equal numbers from three given integers.
    
    Parameters:
    a (int): The first integer.
    b (int): The second integer.
    c (int): The third integer.
    
    Returns:
    int: The count of equal numbers.
    """
    # Initialize a counter for equal numbers
    equal_count = 0
    
    # Check if all three numbers are equal
    if a == b == c:
        equal_count += 1
    
    # Return the count of equal numbers
    return equal_count