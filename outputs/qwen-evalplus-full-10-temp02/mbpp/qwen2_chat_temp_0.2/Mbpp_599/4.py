def sum_average(n):
    # Initialize sum and average
    total_sum = 0
    total_count = 0
    
    # Loop through numbers from 1 to n
    for i in range(1, n + 1):
        # Add the current number to total_sum
        total_sum += i
        # Increment the count of numbers
        total_count += 1
    
    # Calculate the average
    average = total_sum / total_count
    
    # Return the sum and average
    return total_sum, average
