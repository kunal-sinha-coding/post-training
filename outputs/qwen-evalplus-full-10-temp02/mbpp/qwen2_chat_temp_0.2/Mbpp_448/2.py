def cal_sum(n):
    # Initialize the sum to 0
    total_sum = 0
    # Iterate through each number from 1 to n
    for i in range(1, n + 1):
        # Check if the number is a perfect square
        if i * i == n:
            # Add the perfect square to the total sum
            total_sum += i
    return total_sum