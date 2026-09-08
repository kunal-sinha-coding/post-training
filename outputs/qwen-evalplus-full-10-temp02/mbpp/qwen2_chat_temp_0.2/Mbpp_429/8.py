# Define the function to extract elements and tuples from two tuples
def and_tuples(tuple1, tuple2):
    # Use the zip function to iterate over both tuples simultaneously
    # The zip function pairs elements from both tuples
    # The result is a tuple containing tuples from both input tuples
    return tuple(zip(tuple1, tuple2))
