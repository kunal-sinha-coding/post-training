def odd_length_sum(arr):
    # Initialize the sum of odd length subarrays
    sum_odd = 0
    # Iterate through the array
    for i in range(len(arr)):
        # Check if the current index is odd
        if i % 2 != 0:
            # Calculate the sum of odd length subarrays ending at index i
            sum_odd += arr[i]
    return sum_odd