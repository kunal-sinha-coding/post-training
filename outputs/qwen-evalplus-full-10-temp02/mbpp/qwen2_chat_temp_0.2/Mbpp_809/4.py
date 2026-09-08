# Define the function to check if each element of the second tuple is smaller than its corresponding element in the first tuple
def check_smaller(tuple1, tuple2):
    # Iterate over the elements of the second tuple
    for i in range(len(tuple2)):
        # Check if the current element in the second tuple is smaller than the corresponding element in the first tuple
        if tuple2[i] < tuple1[i]:
            # Return False if any element is smaller
            return False
    # If all elements are smaller, return True
    return True