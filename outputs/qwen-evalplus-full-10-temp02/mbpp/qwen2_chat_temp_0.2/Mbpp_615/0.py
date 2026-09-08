def average_tuple(tup):
    # Initialize an empty list to store the average values
    avg_list = []
    # Iterate over each tuple in the input tuple
    for tup in tup:
        # Calculate the sum of the elements in the tuple
        total_sum = sum(tup)
        # Calculate the number of elements in the tuple
        count = len(tup)
        # Calculate the average value for the current tuple
        avg = total_sum / count
        # Append the average value to the list
        avg_list.append(avg)
    # Return the list of average values
    return avg_list