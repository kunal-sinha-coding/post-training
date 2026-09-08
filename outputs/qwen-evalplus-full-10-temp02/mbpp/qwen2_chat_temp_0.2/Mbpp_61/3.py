def count_Substrings(s):
    # Initialize a counter for substrings with the sum of digits equal to their length
    count = 0
    # Iterate through each character in the string
    for i in range(len(s)):
        # Iterate through each character in the substring starting from the current index
        for j in range(i, len(s)):
            # Calculate the sum of digits in the substring
            sum_of_digits = sum(int(digit) for digit in s[i:j+1])
            # If the sum of digits equals the length of the substring, increment the counter
            if sum_of_digits == len(s[i:j+1]):
                count += 1
    return count