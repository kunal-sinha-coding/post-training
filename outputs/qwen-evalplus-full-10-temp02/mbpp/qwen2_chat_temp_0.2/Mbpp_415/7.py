def max_Product(arr):
    # Initialize variables to store the maximum product and the pair
    max_product = arr[0]
    pair = (arr[0], arr[1])
    
    # Iterate through the array starting from the second element
    for i in range(1, len(arr)):
        # Update the maximum product if the current element is greater
        if arr[i] > max_product:
            max_product = arr[i]
            pair = (arr[i], arr[i - 1])
        
        # If the current element is negative and the previous element is positive, update the pair
        elif arr[i] < 0 and arr[i - 1] > 0:
            if arr[i] * arr[i - 1] > max_product:
                max_product = arr[i] * arr[i - 1]
                pair = (arr[i], arr[i - 1])
    
    return pair