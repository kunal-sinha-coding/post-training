def closest_num(n):
    # Initialize the smallest number to a large number
    smallest = float('inf')
    # Iterate through the numbers from 1 to n-1
    for i in range(1, n):
        # Check if the current number is smaller than the smallest number found so far
        if i < smallest:
            smallest = i
    # Return the smallest number found
    return smallest