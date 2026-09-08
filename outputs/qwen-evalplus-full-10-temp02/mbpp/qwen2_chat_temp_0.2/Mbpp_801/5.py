def test_three_equal(a, b, c):
    """
    This function counts the number of equal numbers from three given integers.
    
    Parameters:
    a (int): The first integer.
    b (int): The second integer.
    c (int): The third integer.
    
    Returns:
    int: The count of equal numbers.
    """
    # Initialize a counter for equal numbers
    equal_count = 0
    
    # Iterate through each number to check if it is equal to the others
    for num in [a, b, c]:
        if num == a or num == b or num == c:
            equal_count += 1
    
    return equal_count