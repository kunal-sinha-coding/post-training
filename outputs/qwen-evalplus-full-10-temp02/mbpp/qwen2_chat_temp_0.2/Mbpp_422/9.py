def find_Average_Of_Cube(n):
    # Initialize sum to 0
    sum = 0
    # Loop through the first n natural numbers
    for i in range(1, n + 1):
        # Calculate the cube of the current number
        cube = i ** 3
        # Add the cube to the sum
        sum += cube
    # Calculate the average of the cubes
    average = sum / n
    return average