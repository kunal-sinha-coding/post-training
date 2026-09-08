def perfect_squares(start, end):
    # Initialize an empty list to store perfect squares
    perfect_squares = []
    # Iterate through the range from start to end
    for num in range(start, end + 1):
        # Check if the square of the current number is an integer
        if num ** 0.5 == int(num ** 0.5):
            # If it is, append the number to the list
            perfect_squares.append(num)
    # Return the list of perfect squares
    return perfect_squares