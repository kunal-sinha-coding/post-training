def sum_average(n):
    # Initialize sum and average
    total_sum = 0
    average = 0
    
    # Loop through numbers from 1 to n
    for i in range(1, n + 1):
        # Add the current number to total_sum
        total_sum += i
        # Calculate the average by dividing total_sum by n
        average = total_sum / n
    
    # Return the sum and average
    return total_sum, average
