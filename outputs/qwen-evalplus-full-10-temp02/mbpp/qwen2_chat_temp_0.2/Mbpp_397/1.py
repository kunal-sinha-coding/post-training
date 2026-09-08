def median_numbers(a, b, c):
    # Sort the numbers to find the median
    sorted_numbers = sorted([a, b, c])
    # Return the median
    return sorted_numbers[len(sorted_numbers) // 2]