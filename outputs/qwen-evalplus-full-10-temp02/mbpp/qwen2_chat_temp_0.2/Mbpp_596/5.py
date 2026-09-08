import sys
def tuple_size(input_tuple):
    # Calculate the size of the tuple in bytes
    size = sys.getsizeof(input_tuple)
    return size