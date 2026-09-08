def median_numbers(a, b, c):
    # Sort the three numbers
    sorted_numbers = sorted([a, b, c])
    # Return the middle element of the sorted list
    return sorted_numbers[len(sorted_numbers) // 2]