def average_tuple(tup):
    # Calculate the average for each tuple in the tuple
    avg_list = [sum(tup[i]) / len(tup[i]) for i in range(len(tup))]
    return avg_list