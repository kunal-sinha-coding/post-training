def max_Product(arr):
    # Initialize variables to store the maximum product and the pair
    max_product = arr[0]
    max_pair = (arr[0], arr[1])
    
    # Iterate through the array starting from the second element
    for i in range(1, len(arr)):
        # Update the maximum product if the current product is greater
        if arr[i] > max_product:
            max_product = arr[i]
            max_pair = (arr[i], arr[i-1])
        
        # Update the minimum product if the current product is smaller
        if arr[i] < max_product:
            min_product = arr[i]
    
    # Return the pair with the maximum product
    return max_pair