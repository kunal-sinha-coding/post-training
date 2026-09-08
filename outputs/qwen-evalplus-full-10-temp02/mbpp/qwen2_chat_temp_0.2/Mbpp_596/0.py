import sys

def tuple_size(input_tuple):
    """
    Calculate the size of the given tuple in bytes.
    
    Parameters:
    input_tuple (tuple): The tuple whose size is to be calculated.
    
    Returns:
    int: The size of the tuple in bytes.
    """
    return sys.getsizeof(input_tuple)
