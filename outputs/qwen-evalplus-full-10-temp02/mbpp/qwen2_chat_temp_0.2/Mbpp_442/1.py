def positive_count(arr):
    """
    This function calculates the ratio of positive numbers in an array of integers.
    
    Parameters:
    arr (list): A list of integers.
    
    Returns:
    float: The ratio of positive numbers in the array.
    """
    # Initialize a counter for positive numbers
    positive_count = 0
    
    # Iterate through each number in the array
    for num in arr:
        # Check if the number is positive
        if num > 0:
            # Increment the counter for positive numbers
            positive_count += 1
    
    # Calculate the ratio of positive numbers
    ratio = positive_count / len(arr)
    
    return ratio