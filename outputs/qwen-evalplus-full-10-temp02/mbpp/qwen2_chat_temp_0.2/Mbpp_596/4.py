import sys
def tuple_size(tup):
    # Calculate the size of the tuple in bytes
    size = sys.getsizeof(tup)
    return size