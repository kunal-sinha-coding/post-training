def max_Product(arr):
    # Initialize variables to store the maximum product and the corresponding pair
    max_product = arr[0]
    max_pair = (arr[0], arr[1])
    
    # Iterate through the array starting from the second element
    for i in range(1, len(arr)):
        # If the current element is greater than the maximum product found so far
        if arr[i] > max_product:
            # Update the maximum product and the corresponding pair
            max_product = arr[i]
            max_pair = (arr[i], arr[i - 1])
        
        # If the current element is negative and the product of the pair is negative
        elif arr[i] < 0 and max_product * arr[i] > max_pair[0] * max_pair[1]:
            # Update the maximum product and the corresponding pair
            max_product = arr[i]
            max_pair = (arr[i], arr[i - 1])
    
    # Return the pair with the highest product
    return max_pair