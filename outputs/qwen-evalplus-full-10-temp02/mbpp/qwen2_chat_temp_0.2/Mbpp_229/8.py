def re_arrange_array(arr, n):
    # Separate negative and positive elements
    negatives = [x for x in arr if x < 0]
    positives = [x for x in arr if x >= 0]
    
    # Merge negative and positive elements
    result = negatives + positives
    
    # Return the rearranged array
    return result