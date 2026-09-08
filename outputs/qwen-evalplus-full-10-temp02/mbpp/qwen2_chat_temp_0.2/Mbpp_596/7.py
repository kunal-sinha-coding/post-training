import sys
def tuple_size(test_tup):
    # Calculate the size of the tuple using sys.getsizeof()
    size = sys.getsizeof(test_tup)
    return size