def re_arrange_array(arr, n):
    """
    Rearranges the first n elements of the given array so that all negative elements appear before positive ones, and where the relative order among negative and positive elements is preserved.
    
    :param arr: List of integers
    :param n: Integer representing the number of elements to rearrange
    :return: Rearranged list with negative elements first
    """
    # Separate negative and positive elements
    negative_elements = [x for x in arr if x < 0]
    positive_elements = [x for x in arr if x >= 0]
    
    # Merge negative and positive elements
    result = []
    negative_index = 0
    positive_index = 0
    
    for i in range(n):
        if i < n:
            if negative_index < len(negative_elements):
                result.append(negative_elements[negative_index])
                negative_index += 1
            else:
                result.append(positive_elements[positive_index])
                positive_index += 1
    
    return result
