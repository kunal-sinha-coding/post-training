def reverse_Array_Upto_K(arr, k):
    # Reverse the first k elements of the array
    arr[:k] = arr[k:][::-1]
    return arr