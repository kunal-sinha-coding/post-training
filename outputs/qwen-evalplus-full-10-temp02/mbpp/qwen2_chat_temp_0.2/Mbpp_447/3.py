def cube_nums(lst):
    # Initialize an empty list to store the cubes
    cube_list = []
    # Iterate through each element in the input list
    for num in lst:
        # Calculate the cube of the current number and append it to the cube_list
        cube_list.append(num ** 3)
    # Return the list of cubes
    return cube_list