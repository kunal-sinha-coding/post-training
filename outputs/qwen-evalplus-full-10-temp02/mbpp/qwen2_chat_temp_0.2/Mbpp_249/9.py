def intersection_array(arr1, arr2):
    # Using set intersection to find common elements
    result = list(set(arr1) & set(arr2))
    return result