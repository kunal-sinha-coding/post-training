def difference(n):
    # Calculate the sum of the first n natural numbers
    sum_natural = n * (n + 1) // 2
    
    # Calculate the sum of the cubes of the first n natural numbers
    sum_cubes = n * (n * n * n)
    
    # Calculate the difference between the sum of cubes and the sum of the first n natural numbers
    difference = sum_cubes - sum_natural
    
    return difference