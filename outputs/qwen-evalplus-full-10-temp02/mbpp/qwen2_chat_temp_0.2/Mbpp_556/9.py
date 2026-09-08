def find_Odd_Pair(arr, n):
    count = 0
    # Iterate through each element in the array
    for i in range(n):
        # XOR the current element with all other elements
        for j in range(i + 1, n):
            # Check if the XOR of the current element and the element at index j is odd
            if (arr[i] ^ arr[j]) % 2 != 0:
                count += 1
    return count