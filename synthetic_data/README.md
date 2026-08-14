# Synthetic MBPP Test Data

## Purpose

This directory supports programmatic test augmentation for the 374 tasks in the official MBPP training split.

The first implementation does not generate new semantic tasks. It keeps each task description and reference implementation unchanged, then generates `M` additional test cases for the same function. The default is `M = 5`.

This improves input and edge case coverage. It does not increase the number of algorithms or problem concepts in the training set.

## Training family distribution

MBPP does not provide an official task taxonomy. The categories below are a mutually exclusive working classification based on each task's primary requirement. Secondary capabilities can overlap across categories.

| Primary family | Count | Share | Definition | Representative task IDs |
|---|---:|---:|---|---|
| Lists, arrays, and sequence transformations | 80 | 21.39% | Tasks that filter, rotate, partition, combine, or otherwise transform flat sequences. | 610, 632, 743 |
| Strings and text processing | 64 | 17.11% | Tasks that inspect or transform characters, words, casing, delimiters, and substrings without regex as the primary method. | 602, 604, 668 |
| Number theory and discrete numeric sequences | 50 | 13.37% | Tasks involving primes, divisors, integer sequences, modular arithmetic, digits, or combinatorial numbers. | 605, 681, 876 |
| Tuples, dictionaries, and records | 45 | 12.03% | Tasks whose main operation reads, groups, aggregates, or transforms structured containers. | 611, 653, 902 |
| Ordering, searching, selection, and heaps | 31 | 8.29% | Tasks centered on sorting, binary search, extrema, ranks, heaps, or ordered selection. | 622, 733, 940 |
| Geometry and applied formulas | 27 | 7.22% | Tasks that compute geometric measurements or apply a fixed scientific or statistical formula. | 606, 638, 848 |
| Regex and pattern parsing | 24 | 6.42% | Tasks that primarily recognize, extract, replace, or validate text with regular expressions. | 607, 669, 933 |
| Dynamic programming and combinatorial optimization | 19 | 5.08% | Tasks that optimize or count over overlapping states, recurrences, paths, partitions, or constrained choices. | 608, 689, 918 |
| Basic scalar predicates and domain rules | 16 | 4.28% | Tasks that apply a small decision rule to scalar values or a compact domain table. | 637, 762, 801 |
| Bits and binary representations | 12 | 3.21% | Tasks that inspect, count, rotate, toggle, or otherwise manipulate bits and binary strings. | 633, 671, 799 |
| Matrix, grid, and path problems | 5 | 1.34% | Tasks whose primary data or state is a matrix, grid, triangular array, or constrained path through one. | 642, 721, 834 |
| Trees and graphs | 1 | 0.27% | Tasks whose primary abstraction is a tree or graph. | 927 |
| **Total** | **374** | **100.00%** | The complete official MBPP training split. | |

## Generation approach

The generator processes every training record independently.

1. It parses the existing assertions to identify the required function and observed argument shapes.
2. It selects type aware input mutations that remain close to the demonstrated domain.
3. It includes boundary values, repeated values, reordered values, sign changes, size changes, and structured container mutations when those operations are valid.
4. It executes the reference implementation on each candidate input to obtain the expected output.
5. It rejects inputs that cause a reference error, timeout, nondeterministic result, or unsupported output.
6. It removes duplicate calls and keeps up to `M` accepted tests for each task.
7. It writes deterministic output by using a configured random seed.

The reference implementation is the oracle. A generated assertion is accepted only after the reference code produces its expected value successfully. The generator never asks a language model to infer an answer.

Family labels guide which input mutations are attempted. They do not change the task's required behavior. For example, a list task can receive empty, singleton, duplicate heavy, sorted, and reversed inputs. A string task can receive empty text, repeated characters, whitespace, punctuation, and case variation when the observed contract permits them.

## Output contract

Each generated record should retain the original task identifier, description, reference code, and original tests. It should add the generated tests and generation metadata, including the seed, requested test count, accepted test count, and rejection counts.

Original and generated tests must remain distinguishable. This allows experiments to compare the current reward against reward computed with wider hidden coverage.

## Limitations

This method expands test coverage, not task diversity. All generated cases still measure the same 374 functions.

The original examples may not fully describe valid input domains. Conservative mutation reduces invalid cases, but successful execution by the reference does not prove that an input matches the intended natural language contract.

The reference implementation can contain bugs or accidental behavior. Oracle validation reproduces that behavior rather than correcting it.

Some tasks have narrow domains or formulas that offer few meaningful mutations. Such tasks may produce fewer than `M` unique accepted tests.

Generated cases can still miss important semantic partitions. Programmatic mutation is constrained by the types and values observed in the original tests.

## Usage

The generator entry point will be `generate_tests.py`.

```bash
python synthetic_data/generate_tests.py --tests-per-task 5 --seed 42
```

The command writes `synthetic_data/mbpp_train_tests.jsonl`. The current artifact contains 1,870 generated assertions. Every one of the 374 tasks has exactly five constraint-valid assertions.
