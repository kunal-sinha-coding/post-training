def find_Average_Of_Cube(n):
    # Calculate the sum of the first n natural numbers
    sum_of_natural_numbers = n * (n + 1) // 2
    
    # Calculate the cube of each natural number
    cube_of_natural_numbers = [x**3 for x in range(1, n + 1)]
    
    # Calculate the average of the cubes
    average_of_cubes = sum_of_natural_numbers / len(cube_of_natural_numbers)
    
    return average_of_cubes