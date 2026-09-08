def perfect_squares(start, end):
    # Initialize an empty list to store perfect squares
    perfect_squares = []
    # Iterate through the range from start to end
    for i in range(start, end + 1):
        # Check if the square of the current number is an integer
        if int(i ** 0.5) ** 2 == i:
            # Append the perfect square to the list
            perfect_squares.append(i)
    # Return the list of perfect squares
    return perfect_squares