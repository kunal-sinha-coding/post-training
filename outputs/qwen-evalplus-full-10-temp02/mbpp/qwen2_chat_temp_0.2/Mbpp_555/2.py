def difference(n):
    # Calculate the sum of cubes of the first n natural numbers
    sum_of_cubes = sum(i**3 for i in range(1, n+1))
    # Calculate the sum of the first n natural numbers
    sum_of_natural_numbers = n * (n + 1) // 2
    # Return the difference between the sum of cubes and the sum of natural numbers
    return sum_of_cubes - sum_of_natural_numbers