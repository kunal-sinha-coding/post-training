def re_arrange_array(arr, n):
    """
    Rearranges the first n elements of the given array so that all negative elements appear before positive ones, and where the relative order among negative and positive elements is preserved.
    
    :param arr: List of integers
    :param n: Integer representing the number of elements to rearrange
    :return: Rearranged list
    """
    # Separate negative and positive elements
    negative_elements = [x for x in arr if x < 0]
    positive_elements = [x for x in arr if x >= 0]
    
    # Merge negative and positive elements
    result = negative_elements + positive_elements
    
    # Return the rearranged list
    return result