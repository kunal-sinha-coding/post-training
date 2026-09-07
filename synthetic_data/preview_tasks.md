# Synthetic Task Preview

This file contains the five GPT-5.4 Mini tasks accepted by sandbox validation.

## Task 1: `normalize_license_plate`

Write a function `normalize_license_plate(text)` that normalizes a vehicle license plate string under the following rules:

1. Treat the input as a single plate candidate string that may contain leading/trailing whitespace and internal separators.
2. Remove all spaces, hyphens, and underscores.
3. Convert all letters to uppercase.
4. The remaining characters must be either letters A-Z or digits 0-9; if any other character remains in the cleaned string, return `None`.
5. After cleaning, the plate must contain at least 2 characters and at most 8 characters; otherwise return `None`.
6. The cleaned plate must contain at least one letter and at least one digit; otherwise return `None`.
7. Return the normalized cleaned string if it satisfies all rules.

Examples:
- `normalize_license_plate(" ab-12 ")` -> `"AB12"`
- `normalize_license_plate("x_9")` -> `"X9"`
- `normalize_license_plate("  007  ")` -> `None` (no letter)
- `normalize_license_plate("A!1")` -> `None` (invalid character)

The function must not modify the input string in place and must return either a string or `None`.

### Reference solution

```python

def normalize_license_plate(text):
    if not isinstance(text, str):
        return None
    cleaned = []
    for ch in text.strip():
        if ch in ' -_':
            continue
        if ch.isalpha():
            up = ch.upper()
            if not ('A' <= up <= 'Z'):
                return None
            cleaned.append(up)
        elif ch.isdigit():
            cleaned.append(ch)
        else:
            return None
    if not (2 <= len(cleaned) <= 8):
        return None
    has_letter = any('A' <= ch <= 'Z' for ch in ''.join(cleaned))
    has_digit = any(ch.isdigit() for ch in cleaned)
    if not has_letter or not has_digit:
        return None
    return ''.join(cleaned)

```

### Tests

```python

from types import SimpleNamespace

# Normal cases
assert normalize_license_plate(' ab-12 ') == 'AB12'
assert normalize_license_plate('x_9') == 'X9'
assert normalize_license_plate('Az-09') == 'AZ09'

# Boundary cases
assert normalize_license_plate('a1') == 'A1'
assert normalize_license_plate('a1b2c3d4') == 'A1B2C3D4'
assert normalize_license_plate('a1b2c3d4e') is None  # too long after cleaning

# Invalid / empty cases
assert normalize_license_plate('  007  ') is None  # no letter
assert normalize_license_plate('ABC') is None       # no digit
assert normalize_license_plate('A!1') is None       # invalid character
assert normalize_license_plate(' -_ ') is None      # too short after cleaning
assert normalize_license_plate('') is None
assert normalize_license_plate(None) is None

# Ensure lowercase and mixed separators are handled correctly
assert normalize_license_plate('  m--n__5  ') == 'MN5'
```

## Task 2: `normalize_inventory`

Write a function named `normalize_inventory` that takes a single argument `items`, which must be an iterable of records. Each record must be a 3-element sequence `(category, name, quantity)` where `category` and `name` are strings and `quantity` is an integer. The function must return a list of dictionaries, one per distinct `(category, name)` pair, sorted first by `category` in ascending lexicographic order and then by `name` in ascending lexicographic order. Each dictionary must have keys `category`, `name`, and `quantity`, where `quantity` is the sum of quantities across all matching records.

Input rules:
- If `items` is not iterable, raise `TypeError`.
- If any record is not a 3-element sequence, raise `ValueError`.
- If `category` or `name` is not a string, raise `TypeError`.
- If `quantity` is not an integer, raise `TypeError`.
- If `quantity` is negative, raise `ValueError`.

Additional behavior:
- Ignore records whose `quantity` is zero only for the purpose of summing; they still create a result entry if no other record with the same pair exists.
- The function must not mutate the input.
- If `items` is empty, return an empty list.

Example: `[('fruit', 'apple', 2), ('fruit', 'apple', 1), ('veg', 'carrot', 0)]` should produce `[{'category': 'fruit', 'name': 'apple', 'quantity': 3}, {'category': 'veg', 'name': 'carrot', 'quantity': 0}]`.

### Reference solution

```python

def normalize_inventory(items):
    try:
        iterator = iter(items)
    except TypeError:
        raise TypeError("items must be iterable")

    totals = {}
    for record in iterator:
        if not isinstance(record, (list, tuple)) or len(record) != 3:
            raise ValueError("each record must be a 3-element sequence")
        category, name, quantity = record
        if not isinstance(category, str) or not isinstance(name, str):
            raise TypeError("category and name must be strings")
        if not isinstance(quantity, int):
            raise TypeError("quantity must be an integer")
        if quantity < 0:
            raise ValueError("quantity must not be negative")
        key = (category, name)
        totals[key] = totals.get(key, 0) + quantity

    result = []
    for category, name in sorted(totals.keys()):
        result.append({"category": category, "name": name, "quantity": totals[(category, name)]})
    return result

```

### Tests

```python

from copy import deepcopy

# normal aggregation and sorting
items = [('fruit', 'banana', 1), ('fruit', 'apple', 2), ('fruit', 'apple', 1), ('veg', 'carrot', 0), ('fruit', 'banana', 3)]
original = deepcopy(items)
assert normalize_inventory(items) == [
    {'category': 'fruit', 'name': 'apple', 'quantity': 3},
    {'category': 'fruit', 'name': 'banana', 'quantity': 4},
    {'category': 'veg', 'name': 'carrot', 'quantity': 0},
]
assert items == original  # input not mutated

# empty input
assert normalize_inventory([]) == []

# boundary: single zero quantity record still appears
assert normalize_inventory([('tools', 'hammer', 0)]) == [
    {'category': 'tools', 'name': 'hammer', 'quantity': 0}
]

# invalid: non-iterable items
try:
    normalize_inventory(None)
    raise AssertionError('TypeError expected for non-iterable input')
except TypeError:
    pass

# invalid: bad record length
try:
    normalize_inventory([('fruit', 'apple')])
    raise AssertionError('ValueError expected for malformed record')
except ValueError:
    pass

# invalid: wrong types
try:
    normalize_inventory([('fruit', 123, 1)])
    raise AssertionError('TypeError expected for non-string name')
except TypeError:
    pass

# invalid: negative quantity
try:
    normalize_inventory([('fruit', 'apple', -1)])
    raise AssertionError('ValueError expected for negative quantity')
except ValueError:
    pass

```

## Task 3: `encode_interval_runs`

Implement a function `encode_interval_runs(intervals)` that takes a list of integer closed intervals represented as 2-element lists or tuples `[start, end]` or `(start, end)`. The function must first normalize each interval so that `start <= end` by swapping endpoints if needed. Then it must merge all intervals that overlap or touch, where two intervals [a, b] and [c, d] are considered mergeable if `c <= b + 1` after sorting by start. The result must be a list of merged intervals in ascending order, each as a 2-element list `[start, end]`.

Behavior details:
- Ignore duplicate intervals after normalization; they should not affect the output.
- The input may be empty, in which case return an empty list.
- The function must not mutate the input list or any nested interval objects.
- A single interval should be returned as `[[start, end]]` after normalization.
- Intervals may contain negative integers and very large integers.
- If an element of `intervals` is not a length-2 list/tuple of integers, raise `TypeError`.
- If any interval contains a non-integer endpoint, raise `TypeError`.


### Reference solution

```python

def encode_interval_runs(intervals):
    normalized = []
    seen = set()

    for item in intervals:
        if not isinstance(item, (list, tuple)) or len(item) != 2:
            raise TypeError("each interval must be a length-2 list or tuple of integers")
        a, b = item
        if not isinstance(a, int) or not isinstance(b, int):
            raise TypeError("interval endpoints must be integers")
        start, end = (a, b) if a <= b else (b, a)
        key = (start, end)
        if key not in seen:
            seen.add(key)
            normalized.append([start, end])

    if not normalized:
        return []

    normalized.sort(key=lambda x: (x[0], x[1]))
    merged = [normalized[0][:]]

    for start, end in normalized[1:]:
        last = merged[-1]
        if start <= last[1] + 1:
            if end > last[1]:
                last[1] = end
        else:
            merged.append([start, end])

    return merged

```

### Tests

```python

from copy import deepcopy

# normal merging with touching intervals
inp = [[5, 7], [1, 2], [3, 4], [8, 8]]
assert encode_interval_runs(inp) == [[1, 8]]
assert inp == [[5, 7], [1, 2], [3, 4], [8, 8]]

# normalization of reversed endpoints and duplicate elimination
assert encode_interval_runs([(4, 2), [2, 4], [10, 12], (12, 10)]) == [[2, 4], [10, 12]]

# negative numbers and multiple merged components
assert encode_interval_runs([[-10, -8], [-7, -7], [-6, -4], [0, 1], [2, 2], [4, 3]]) == [[-10, -4], [0, 4]]

# empty input
assert encode_interval_runs([]) == []

# single interval and immutability of nested objects
one = [[9, 3]]
copy_before = deepcopy(one)
assert encode_interval_runs(one) == [[3, 9]]
assert one == copy_before

# invalid shapes
for bad in ([1, 2, 3], [1], 5, None, [[1, 2, 3]]):
    try:
        encode_interval_runs(bad)
        assert False, f"expected TypeError for {bad!r}"
    except TypeError:
        pass

# invalid endpoint types
for bad in ([[1, 2.0]], [["1", 2]], [(1, None)]):
    try:
        encode_interval_runs(bad)
        assert False, f"expected TypeError for {bad!r}"
    except TypeError:
        pass

# very large integers should be handled and merged when touching
big = 10**18
assert encode_interval_runs([[big, big + 1], [big + 2, big + 2]]) == [[big, big + 2]]

```

## Task 4: `normalize_event_title`

Implement a function `normalize_event_title(title: str) -> str` that converts a raw event title into a canonical display form.

Rules:
1. Split the input on any whitespace. Leading, trailing, and repeated internal whitespace should be ignored.
2. Remove surrounding punctuation from each word, where punctuation means any character for which `str.isalnum()` is False. This includes symbols like `-`, `_`, `!`, `(`, `)`, etc. Punctuation inside a word should also be stripped if it is at either end after whitespace splitting.
3. After stripping punctuation, discard any empty words.
4. Convert all remaining words to title case with these special rules:
   - The first character of each word must be uppercase if it is a letter.
   - All remaining alphabetic characters in that word must be lowercase.
   - Non-alphabetic characters inside a word must be preserved.
5. Join the normalized words with a single space.
6. If no words remain after normalization, return the empty string.

Examples:
- `normalize_event_title("  annual   tech! conference 2026  ")` should return `"Annual Tech Conference 2026"`
- `normalize_event_title("__python--workshop__")` should return `"Python--workshop"`
- `normalize_event_title("!!!")` should return `""`

### Reference solution

```python

def normalize_event_title(title: str) -> str:
    words = title.split()
    normalized = []

    for word in words:
        start = 0
        end = len(word)
        while start < end and not word[start].isalnum():
            start += 1
        while end > start and not word[end - 1].isalnum():
            end -= 1
        core = word[start:end]
        if not core:
            continue

        first = core[0]
        if first.isalpha():
            first = first.upper()
        rest = []
        for ch in core[1:]:
            rest.append(ch.lower() if ch.isalpha() else ch)
        normalized.append(first + ''.join(rest))

    return ' '.join(normalized)

```

### Tests

```python

from typing import Callable

# Basic normalization and whitespace collapsing
assert normalize_event_title("  annual   tech! conference 2026  ") == "Annual Tech Conference 2026"

# Punctuation stripped from both ends of each token
assert normalize_event_title("__python--workshop__") == "Python--workshop"

# Mixed punctuation, case normalization, and internal non-alpha characters preserved
assert normalize_event_title("(PyThOn) 3.11--beta!!") == "Python 3.11--beta"

# Words containing embedded punctuation are only normalized by case, not split
assert normalize_event_title("co-op DEVELOPER_day") == "Co-op Developer_day"

# Empty or punctuation-only input returns empty string
assert normalize_event_title("") == ""
assert normalize_event_title("   !!!   ___   ") == ""

# Single word boundary cases
assert normalize_event_title("x") == "X"
assert normalize_event_title("7up!") == "7up"

```

## Task 5: `summarize_runs`

Implement a function `summarize_runs(seq)` that analyzes a sequence of integers as a run-length summary.

Rules:
- `seq` must be a list of integers. If `seq` is not a list, raise `TypeError`.
- If any element of `seq` is not an integer (excluding booleans), raise `TypeError`.
- The function must return a tuple `(longest_run_length, longest_run_value, run_count)` where:
  - `longest_run_length` is the length of the longest contiguous block of equal values.
  - `longest_run_value` is the value appearing in the first longest block. If `seq` is empty, this must be `None`.
  - `run_count` is the number of contiguous blocks in the sequence.
- A run is a maximal contiguous segment of equal integers.
- For ties in longest run length, choose the value from the earliest such run.
- For an empty list, return `(0, None, 0)`.

Examples:
- `summarize_runs([1, 1, 2, 2, 2, 3])` returns `(3, 2, 3)`
- `summarize_runs([5, 5, 1, 1])` returns `(2, 5, 2)`
- `summarize_runs([])` returns `(0, None, 0)`

### Reference solution

```python

def summarize_runs(seq):
    if not isinstance(seq, list):
        raise TypeError("seq must be a list")
    for x in seq:
        if isinstance(x, bool) or not isinstance(x, int):
            raise TypeError("all elements must be integers")
    if not seq:
        return (0, None, 0)
    run_count = 1
    longest_run_length = 1
    longest_run_value = seq[0]
    current_value = seq[0]
    current_length = 1
    for x in seq[1:]:
        if x == current_value:
            current_length += 1
        else:
            run_count += 1
            if current_length > longest_run_length:
                longest_run_length = current_length
                longest_run_value = current_value
            current_value = x
            current_length = 1
    if current_length > longest_run_length:
        longest_run_length = current_length
        longest_run_value = current_value
    return (longest_run_length, longest_run_value, run_count)

```

### Tests

```python

from math import inf

# Basic behavior
assert summarize_runs([1, 1, 2, 2, 2, 3]) == (3, 2, 3)
assert summarize_runs([5, 5, 1, 1]) == (2, 5, 2)
assert summarize_runs([9]) == (1, 9, 1)

# Tie handling: earliest longest run wins
assert summarize_runs([4, 4, 7, 7]) == (2, 4, 2)
assert summarize_runs([1, 1, 2, 2, 3]) == (2, 1, 3)

# Empty input
assert summarize_runs([]) == (0, None, 0)

# More complex run structure
assert summarize_runs([3, 3, 3, 2, 2, 1, 1, 1, 1, 2]) == (4, 1, 4)
assert summarize_runs([0, 0, 0, 0]) == (4, 0, 1)

# Invalid inputs
try:
    summarize_runs((1, 1, 2))
    assert False, "Expected TypeError for non-list input"
except TypeError:
    pass

try:
    summarize_runs([1, 2.0, 2])
    assert False, "Expected TypeError for non-integer element"
except TypeError:
    pass

try:
    summarize_runs([True, 1])
    assert False, "Expected TypeError for boolean element"
except TypeError:
    pass
```
