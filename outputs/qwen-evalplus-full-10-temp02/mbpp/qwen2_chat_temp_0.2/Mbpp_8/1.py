def square_nums(nums):
    # Initialize an empty list to store the squares of the numbers
    squares = []
    # Iterate through each number in the input list
    for num in nums:
        # Square the number and append it to the squares list
        squares.append(num ** 2)
    # Return the list of squares
    return squares