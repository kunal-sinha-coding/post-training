# Define the function to compute the n-th power of each number in a list
def nth_nums(numbers, n):
    # Initialize an empty list to store the results
    result = []
    # Iterate through each number in the input list
    for num in numbers:
        # Calculate the n-th power of the current number
        power = num ** n
        # Append the result to the result list
        result.append(power)
    # Return the list of results
    return result
