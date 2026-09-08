def count_reverse_pairs(strings):
    count = 0
    for i in range(len(strings)):
        for j in range(i + 1, len(strings)):
            if strings[i] == strings[j][::-1]:
                count += 1
    return count