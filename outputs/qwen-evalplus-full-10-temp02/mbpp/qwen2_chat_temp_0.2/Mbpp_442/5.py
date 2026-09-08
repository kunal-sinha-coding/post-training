def positive_count(arr):
    # Initialize a counter for positive numbers
    count = 0
    # Iterate through each number in the array
    for num in arr:
        # Check if the number is positive
        if num > 0:
            # Increment the counter
            count += 1
    # Calculate the ratio of positive numbers to the total number of elements
    ratio = count / len(arr)
    return ratio