# Define the function to find cubes of individual elements in a list
def cube_nums(nums):
    # Initialize an empty list to store the cubes
    cubes = []
    # Iterate over each number in the input list
    for num in nums:
        # Calculate the cube of the current number and append it to the cubes list
        cubes.append(num ** 3)
    # Return the list of cubes
    return cubes