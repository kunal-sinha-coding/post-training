def cube_nums(nums):
    # Initialize an empty list to store the cubes of the elements
    cubes = []
    # Iterate through each element in the input list
    for num in nums:
        # Calculate the cube of the current number and append it to the cubes list
        cubes.append(num ** 3)
    # Return the list of cubes
    return cubes