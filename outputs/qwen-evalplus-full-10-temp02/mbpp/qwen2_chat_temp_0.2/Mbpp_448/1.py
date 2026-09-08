def cal_sum(n):
    # Initialize the sum to 0
    total_sum = 0
    # Iterate through each number from 1 to n
    for i in range(1, n + 1):
        # Check if the number is a perfect square
        if int(i**0.5)**2 == i:
            # Add the perfect square to the total sum
            total_sum += i
    # Return the total sum of perfect squares
    return total_sum