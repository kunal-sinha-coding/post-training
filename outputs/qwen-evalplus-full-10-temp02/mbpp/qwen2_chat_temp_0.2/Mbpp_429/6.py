# Define the function to extract elements from two tuples
def and_tuples(tuple1, tuple2):
    # Use the zip function to pair elements from both tuples
    result = tuple(zip(tuple1, tuple2))
    # Return the result as a tuple
    return result
