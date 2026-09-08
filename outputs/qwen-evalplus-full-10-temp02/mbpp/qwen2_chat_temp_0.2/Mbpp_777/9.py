def find_sum(lst):
    # Initialize the sum to 0
    total_sum = 0
    # Create a set to store unique elements
    unique_elements = set(lst)
    # Iterate through each element in the list
    for element in unique_elements:
        # Add the element to the total sum
        total_sum += element
    # Return the total sum of non-repeated elements
    return total_sum