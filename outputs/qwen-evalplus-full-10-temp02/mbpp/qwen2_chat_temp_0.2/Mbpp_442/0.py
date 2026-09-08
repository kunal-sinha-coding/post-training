def positive_count(arr):
    # Initialize a counter for positive numbers
    positive_count = 0
    # Iterate through each number in the array
    for num in arr:
        # Check if the number is positive
        if num > 0:
            # Increment the counter if the number is positive
            positive_count += 1
    # Calculate the ratio of positive numbers to the total number of elements in the array
    ratio = positive_count / len(arr)
    return ratio