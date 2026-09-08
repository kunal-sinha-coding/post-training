def count_Substrings(s):
    # Initialize the count of substrings
    count = 0
    # Iterate through the string
    for i in range(len(s)):
        # Iterate through the substring starting from the current index
        for j in range(i, len(s) + 1):
            # Calculate the sum of digits in the substring
            sum_of_digits = sum(int(digit) for digit in s[i:j])
            # Check if the sum of digits is equal to the length of the substring
            if sum_of_digits == len(s[i:j]):
                count += 1
    return count
