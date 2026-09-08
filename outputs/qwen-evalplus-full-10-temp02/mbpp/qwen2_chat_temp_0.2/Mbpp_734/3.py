def sum_Of_Subarray_Prod(arr):
    # Initialize variables to store the sum of products and the maximum product found
    sum_prod = 1
    max_prod = arr[0]
    # Iterate through the array starting from the second element
    for i in range(1, len(arr)):
        # Update the sum of products by multiplying the current element with the sum of products found so far
        sum_prod = sum_prod * arr[i]
        # Update the maximum product found if the current element is greater than the maximum product found so far
        max_prod = max(max_prod, arr[i])
    # Return the sum of products
    return sum_prod