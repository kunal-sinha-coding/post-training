def square_nums(lst):
    # Initialize an empty list to store the squares
    squares = []
    # Iterate through each element in the input list
    for num in lst:
        # Square the current number and append it to the squares list
        squares.append(num ** 2)
    # Return the list of squares
    return squares