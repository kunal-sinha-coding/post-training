def find_Average_Of_Cube(n):
    # Initialize the sum of cubes to 0
    sum_of_cubes = 0
    # Loop through the first n natural numbers
    for i in range(1, n + 1):
        # Add the cube of the current number to the sum
        sum_of_cubes += i ** 3
    # Calculate the average of the cubes
    average = sum_of_cubes / n
    # Return the average
    return average