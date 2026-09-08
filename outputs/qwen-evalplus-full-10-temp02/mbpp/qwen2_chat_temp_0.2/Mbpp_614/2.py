def cummulative_sum(tup_list):
    # Initialize the sum variable to 0
    total_sum = 0
    # Iterate through each tuple in the list
    for tup in tup_list:
        # Add the sum of the tuple to the total sum
        total_sum += sum(tup)
    # Return the total sum
    return total_sum