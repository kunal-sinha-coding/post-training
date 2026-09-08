def re_arrange_array(arr, n):
    # Separate negative and positive elements
    negative_elements = [x for x in arr if x < 0]
    positive_elements = [x for x in arr if x >= 0]
    
    # Merge negative and positive elements
    result = []
    i = 0
    j = 0
    
    # Iterate through the array
    for x in arr:
        if x < 0:
            result.append(negative_elements[i])
            i += 1
        else:
            result.append(positive_elements[j])
            j += 1
    
    return result
