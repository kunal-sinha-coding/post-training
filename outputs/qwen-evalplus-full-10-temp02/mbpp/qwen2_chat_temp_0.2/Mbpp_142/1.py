def count_samepair(list1, list2, list3):
    # Initialize a counter for identical elements
    count = 0
    # Iterate through each element in the first list
    for i in range(len(list1)):
        # Check if the element is present in all three lists
        if list1[i] in list2 and list1[i] in list3:
            count += 1
    return count