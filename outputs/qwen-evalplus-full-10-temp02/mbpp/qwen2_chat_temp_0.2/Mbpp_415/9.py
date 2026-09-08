def max_Product(arr):
    # Initialize variables to store the maximum product and the pair with the maximum product
    max_product = arr[0]
    max_pair = (arr[0], arr[1])
    
    # Iterate through the array starting from the second element
    for i in range(1, len(arr)):
        # Update the maximum product if the current element is greater
        if arr[i] > max_product:
            max_product = arr[i]
            max_pair = (arr[i], arr[i - 1])
        
        # Update the pair with the maximum product if the current element is less than the maximum product
        elif arr[i] < max_product:
            if arr[i] * max_pair[0] > max_product:
                max_product = arr[i] * max_pair[0]
                max_pair = (arr[i], arr[i - 1])
    
    # Return the pair with the maximum product
    return max_pair