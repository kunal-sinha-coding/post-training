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
    result = []
    i = 0
    j = 0
    
    # Iterate through the array
    for _ in range(n):
        if i < len(negative_elements):
            result.append(negative_elements[i])
            i += 1
        if j < len(positive_elements):
            result.append(positive_elements[j])
            j += 1
    
    return result
