def find_Average_Of_Cube(n):
    # Calculate the sum of the first n natural numbers
    sum_of_natural_numbers = n * (n + 1) // 2
    
    # Calculate the average of the cubes of the first n natural numbers
    average_of_cubes = sum_of_natural_numbers ** (1/3)
    
    return average_of_cubes