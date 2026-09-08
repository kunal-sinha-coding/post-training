def intersection_array(arr1, arr2):
    # Use set intersection to find common elements between the two arrays
    result = list(set(arr1) & set(arr2))
    return result