def test_three_equal(a, b, c):
    # Initialize a counter for equal numbers
    equal_count = 0
    # Iterate through the three numbers
    for num in [a, b, c]:
        # Check if the current number is equal to the first number
        if num == a:
            equal_count += 1
        # Check if the current number is equal to the second number
        elif num == b:
            equal_count += 1
        # Check if the current number is equal to the third number
        elif num == c:
            equal_count += 1
    # Return the total count of equal numbers
    return equal_count