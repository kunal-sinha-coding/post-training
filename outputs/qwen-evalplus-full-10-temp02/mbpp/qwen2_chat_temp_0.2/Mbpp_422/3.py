def find_Average_Of_Cube(n):
    # Initialize the sum of cubes to 0
    sum_of_cubes = 0
    # Loop through the first n natural numbers
    for i in range(1, n + 1):
        # Add the cube of the current number to the sum
        sum_of_cubes += i ** 3
    # Calculate the average by dividing the sum of cubes by n
    average = sum_of_cubes / n
    return average