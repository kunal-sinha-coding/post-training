def extract_nth_element(tuples_list, n):
    # Extract the nth element from each tuple in the list
    nth_elements = [tuples_list[i][n] for i in range(len(tuples_list))]
    return nth_elements
