def perfect_squares(start, end):
    # Initialize an empty list to store perfect squares
    perfect_squares = []
    
    # Iterate through the range from start to end
    for num in range(start, end + 1):
        # Check if the square of the current number is a perfect square
        if num ** 0.5 == int(num ** 0.5):
            # Append the perfect square to the list
            perfect_squares.append(num ** 2)
    
    # Return the list of perfect squares
    return perfect_squares