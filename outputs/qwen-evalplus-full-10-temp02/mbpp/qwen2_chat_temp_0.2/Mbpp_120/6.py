def max_product_tuple(tuples_list):
    # Initialize the maximum product to the first tuple in the list
    max_product = tuples_list[0][0] * tuples_list[0][1]
    
    # Iterate through the list of tuples
    for i in range(len(tuples_list)):
        # Calculate the product of each pair of tuples
        product = tuples_list[i][0] * tuples_list[i][1]
        
        # Update the maximum product if the current product is greater
        if product > max_product:
            max_product = product
    
    return max_product