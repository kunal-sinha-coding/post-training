def median_numbers(a, b, c):
    # Sort the three numbers
    numbers = sorted([a, b, c])
    # Return the middle number
    return numbers[len(numbers) // 2]