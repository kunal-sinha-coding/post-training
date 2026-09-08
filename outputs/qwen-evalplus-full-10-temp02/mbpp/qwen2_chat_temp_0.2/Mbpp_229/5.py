def re_arrange_array(arr, n):
    # Separate negative and positive elements
    negative_elements = [x for x in arr if x < 0]
    positive_elements = [x for x in arr if x >= 0]
    
    # Merge negative and positive elements
    result = []
    while negative_elements:
        result.append(negative_elements.pop(0))
    while positive_elements:
        result.append(positive_elements.pop(0))
    
    return result
