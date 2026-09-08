def median_numbers(num1, num2, num3):
    # Sort the numbers to find the median
    sorted_numbers = sorted([num1, num2, num3])
    # Return the median
    return sorted_numbers[len(sorted_numbers) // 2]