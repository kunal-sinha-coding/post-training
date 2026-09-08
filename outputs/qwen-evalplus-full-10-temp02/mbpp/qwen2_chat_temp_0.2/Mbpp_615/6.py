def average_tuple(tup_list):
    # Initialize an empty list to store the average values
    avg_list = []
    # Iterate over each tuple in the input list
    for tup in tup_list:
        # Calculate the sum of the elements in the tuple
        total_sum = sum(tup)
        # Calculate the average by dividing the total sum by the number of elements in the tuple
        avg = total_sum / len(tup)
        # Append the average to the list
        avg_list.append(avg)
    # Return the list of average values
    return avg_list
