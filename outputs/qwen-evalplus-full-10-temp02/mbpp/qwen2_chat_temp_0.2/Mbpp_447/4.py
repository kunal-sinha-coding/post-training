def cube_nums(lst):
    # Initialize an empty list to store the cubes
    cubes = []
    # Iterate through each element in the input list
    for num in lst:
        # Calculate the cube of the current number
        cube = num ** 3
        # Append the cube to the cubes list
        cubes.append(cube)
    # Return the list of cubes
    return cubes