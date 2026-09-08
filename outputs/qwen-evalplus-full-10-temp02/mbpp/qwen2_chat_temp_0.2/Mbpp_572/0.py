def two_unique_nums(nums):
    # Convert the list of lists into a set to remove duplicates
    unique_nums = set(nums)
    # Convert the set back to a list and return
    return list(unique_nums)