def difference(n):
    # Calculate the sum of the first n natural numbers
    sum_natural = n * (n + 1) // 2
    
    # Calculate the sum of the cubes of the first n natural numbers
    sum_cubes = n * (n * n * n)
    
    # Return the difference between the sum of cubes and the sum of the first n natural numbers
    return sum_cubes - sum_natural