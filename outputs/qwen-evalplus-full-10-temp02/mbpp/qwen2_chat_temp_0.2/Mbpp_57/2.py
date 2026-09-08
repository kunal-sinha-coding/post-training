def find_Max_Num(digits):
    # Convert the list of digits to a string
    num_str = ''.join(map(str, digits))
    # Sort the string in descending order
    sorted_str = sorted(num_str, reverse=True)
    # Convert the sorted string back to a list of integers
    sorted_list = list(map(int, sorted_str))
    # Return the maximum number from the sorted list
    return max(sorted_list)