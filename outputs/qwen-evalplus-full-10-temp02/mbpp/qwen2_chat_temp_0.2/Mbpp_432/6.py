def median_trapezium(a, b, c):
    # Calculate the length of the trapezium
    length = a + b + c
    # Sort the trapezium in ascending order
    sorted_trapezium = sorted([a, b, c])
    # Calculate the median length
    median = sorted_trapezium[len(sorted_trapezium) // 2]
    return median