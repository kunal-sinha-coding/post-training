def re_arrange_array(arr, n):
    # Separate negative and positive elements
    negative_elements = [x for x in arr if x < 0]
    positive_elements = [x for x in arr if x >= 0]
    
    # Merge the two lists
    result = negative_elements + positive_elements
    
    # Return the rearranged array
    return result