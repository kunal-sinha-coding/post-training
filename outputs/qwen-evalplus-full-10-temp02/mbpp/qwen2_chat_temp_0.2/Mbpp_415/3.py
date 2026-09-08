def max_Product(arr):
    # Initialize variables to store the maximum product and the pair
    max_product = arr[0]
    pair = (arr[0], arr[1])
    
    # Iterate through the array starting from the second element
    for i in range(1, len(arr)):
        # Update the maximum product if the current product is greater
        if arr[i] > max_product:
            max_product = arr[i]
            pair = (arr[i], arr[i-1])
        
        # Update the pair if the current product is less than the maximum product
        elif arr[i] < max_product:
            # Check if the current pair is different from the previous one
            if (arr[i], arr[i-1]) != pair:
                max_product = arr[i]
                pair = (arr[i], arr[i-1])
    
    # Return the pair with the highest product
    return pair