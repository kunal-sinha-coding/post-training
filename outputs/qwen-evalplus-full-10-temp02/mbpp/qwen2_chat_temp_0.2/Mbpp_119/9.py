def search(arr):
    """
    This function takes a sorted array as input and returns the element that appears only once.
    
    :param arr: A list of integers
    :return: The element that appears only once in the array
    """
    # Initialize a variable to store the result
    result = arr[0]
    # Iterate through the array starting from the second element
    for i in range(1, len(arr)):
        # If the current element is not equal to the previous one, update the result
        if arr[i] != arr[i - 1]:
            result = arr[i]
    return result