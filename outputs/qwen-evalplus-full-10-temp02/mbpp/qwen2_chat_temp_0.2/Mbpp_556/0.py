def find_Odd_Pair(arr, n):
    count = 0
    for i in range(n):
        for j in range(i + 1, n):
            if (arr[i] ^ arr[j]) % 2 != 0:
                count += 1
    return count