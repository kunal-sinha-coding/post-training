def comb_sort(arr):
    n = len(arr)
    gap = 1
    while gap < n:
        for i in range(0, n - gap, gap):
            if arr[i] > arr[i + gap]:
                arr[i], arr[i + gap] = arr[i + gap], arr[i]
        gap *= 2
    return arr