def test_three_equal(a, b, c):
    # Initialize a counter for equal numbers
    equal_count = 0
    
    # Iterate through each number
    for num in [a, b, c]:
        # Check if the current number is equal to the previous ones
        if num == a or num == b or num == c:
            equal_count += 1
    
    # Return the total count of equal numbers
    return equal_count