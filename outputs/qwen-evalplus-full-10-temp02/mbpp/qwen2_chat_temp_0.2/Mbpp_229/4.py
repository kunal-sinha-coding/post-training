def re_arrange_array(arr, n):
    """
    Rearranges the first n elements of the given array so that all negative elements appear before positive ones, and where the relative order among negative and positive elements is preserved.
    
    Parameters:
    arr (list): The input array.
    n (int): The number of elements to rearrange.
    
    Returns:
    list: The rearranged array.
    """
    # Separate negative and positive elements
    negative_elements = [x for x in arr if x < 0]
    positive_elements = [x for x in arr if x >= 0]
    
    # Merge the negative and positive elements
    result = negative_elements + positive_elements
    
    # Return the rearranged array
    return result
