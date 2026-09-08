def and_tuples(tup1, tup2):
    # Extract the elementwise elements from the first tuple
    elementwise = tuple(a * b for a, b in zip(tup1, tup2))
    # Extract the tuples from the second tuple
    tuples = tuple(tup for tup in tup2 if isinstance(tup, tuple))
    return elementwise, tuples
