def count_samepair(list1, list2, list3):
    # Initialize a counter for identical elements
    count = 0
    # Iterate through the first list
    for i in range(len(list1)):
        # Check if the current element is identical in all three lists
        if list1[i] == list2[i] == list3[i]:
            count += 1
    return count