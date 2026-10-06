# MBPP Training Taxonomy for 10x Prompt Generation

This taxonomy assigns one primary category to each task in the effective checkpoint-830 training pool. Labels use task descriptions and the requested operation. The two normalized wording duplicates with EvalPlus tasks, IDs 217 and 928, are excluded.

The pool has 591 tasks. The prompt set has 5319 prompts. Each category receives nine synthetic prompts for each existing task, so the combined dataset target is 5910 tasks.

| Category | Existing tasks | Synthetic prompts | Combined tasks |
| --- | ---: | ---: | ---: |
| Arithmetic and numeric formulas | 38 | 342 | 380 |
| Number properties and number theory | 78 | 702 | 780 |
| Lists and sequence transformations | 62 | 558 | 620 |
| Search, sorting, and selection | 68 | 612 | 680 |
| Counting and frequency | 50 | 450 | 500 |
| Strings and text processing | 77 | 693 | 770 |
| Set and membership operations | 20 | 180 | 200 |
| Mappings, tuples, and record aggregation | 50 | 450 | 500 |
| Recurrence, combinatorics, and dynamic programming | 52 | 468 | 520 |
| Matrices and grids | 6 | 54 | 60 |
| Geometry and spatial calculations | 38 | 342 | 380 |
| Graphs, paths, intervals, and chains | 6 | 54 | 60 |
| Predicates, validation, and classification | 46 | 414 | 460 |

## Arithmetic and numeric formulas

38 existing tasks and 342 synthetic prompts.

Compute numeric results from arithmetic rules, rates, conversions, or numeric formulas.

- 35: Write a function to find the n-th rectangular number.
- 38: Write a function to find the division of first even and odd number of a given list.
- 136: Write a function to calculate electricity bill.
- 144: Write a python function to find the sum of absolute differences in all pairs of the given array.
- 158: Write a python function to find k number of operations required to make all elements equal.
- 212: Write a python function to find the sum of fourth power of n natural numbers.
- 214: Write a function to convert radians to degrees.
- 218: Write a python function to find the minimum operations required to make two numbers equal.
- 246: Write a function for computing square roots using the babylonian method.
- 248: Write a function to calculate the harmonic sum of n-1.
- 289: Write a python function to calculate the number of odd days in a given year.
- 320: Write a function to calculate the difference between the squared sum of first n natural numbers and the sum of squared first n natural numbers.
- 335: Write a function to find the sum of arithmetic progression.
- 354: Write a function to find t-nth term of arithemetic progression.
- 375: Write a function to round the given number to the nearest multiple of a specific number.
- 452: Write a function that gives loss amount if the given amount has loss else return none.
- 486: Write a function to compute binomial probability for the given number.
- 491: Write a function to find the sum of geometric progression series.
- 502: Write a python function to find remainder of two numbers.
- 504: Write a python function to find the cube sum of first n natural numbers.
- 509: Write a python function to find the average of odd numbers till a given odd number.
- 543: Write a function to add two numbers and print number of digits of sum.
- 549: Write a python function to find the sum of fifth power of first n odd natural numbers.
- 609: Write a python function to find minimum possible value for the given periodic function.
- 634: Write a python function to find the sum of fourth power of first n even natural numbers.
- 655: Write a python function to find the sum of fifth power of n natural numbers.
- 664: Write a python function to find the average of even numbers till a given even number.
- 675: Write a function to add two integers. however, if the sum is between the given range it will return 20.
- 688: Write a function to get the length of a complex number.
- 830: Write a function to round up a number to specific digits.
- 837: Write a python function to find the cube sum of first n odd natural numbers.
- 880: Write a python function to find number of solutions in quadratic equation.
- 901: Write a function to find the smallest multiple of the first n numbers.
- 931: Write a function to calculate the sum of series 1³+2³+3³+….+n³.
- 935: Write a function to calculate the sum of series 1²+2²+3²+….+n².
- 954: Write a function that gives profit amount if the given amount has profit else return none.
- 962: Write a python function to find the sum of all even natural numbers within the range l and r.
- 963: Write a function to calculate the discriminant value.

## Number properties and number theory

78 existing tasks and 702 synthetic prompts.

Work with integer properties, divisibility, prime factors, digits, bit operations, or numeric representations.

- 21: Write a function to find m number of multiples of n.
- 24: Write a function to convert the given binary number to its decimal equivalent.
- 32: Write a python function to find the largest prime factor of a given number.
- 33: Write a python function to convert a decimal number to binary number.
- 36: Write a python function to find the nth digit in the proper fraction of two given numbers.
- 45: Write a function to find the gcd of the given array elements.
- 47: Write a python function to find the last digit when factorial of a divides factorial of b.
- 48: Write a python function to set all odd bits of a given number.
- 78: Write a python function to find number of integers with odd number of set bits.
- 107: Write a python function to count hexadecimal numbers for a given range.
- 122: Write a function to find n’th smart number.
- 148: Write a function to divide a number into two parts such that the sum of digits is maximum.
- 150: Write a python function to find whether the given number is present in the infinite sequence or not.
- 151: Write a python function to check whether the given number is co-prime or not.
- 155: Write a python function to toggle all even bits of a given number.
- 164: Write a python function to check whether the sum of divisors are same or not.
- 177: Write a python function to find two distinct numbers such that their lcm lies within the given range.
- 179: Write a function to find if the given number is a keith number or not.
- 188: Write a python function to check whether the given number can be represented by product of two squares or not.
- 194: Write a python function to convert octal number to decimal number.
- 199: Write a python function to find highest power of 2 less than or equal to given number.
- 203: Write a python function to find the hamming distance between given two integers.
- 211: Write a python function to count numbers whose oth and nth bits are set.
- 228: Write a python function to check whether all the bits are unset in the given range or not.
- 288: Write a function to count array elements having modular inverse under given prime number p equal to itself.
- 295: Write a function to return the sum of all divisors of a number.
- 302: Write a python function to find the most significant bit number which is also a set bit.
- 321: Write a function to find the demlo number for the given number.
- 331: Write a python function to count unset bits of a given number.
- 339: Write a python function to find the maximum occuring divisor in an interval.
- 344: Write a python function to find number of elements with odd factors in a given range.
- 365: Write a python function to count the number of digits of a given number.
- 383: Write a python function to toggle all odd bits of a given number.
- 399: Write a function to perform the mathematical bitwise xor operation across the given tuples.
- 407: Write a function to create the next bigger number by rearranging the digits of a given number.
- 467: Write a python function to convert decimal number to octal number.
- 483: Write a python function to find the first natural number whose factorial is divisible by x.
- 494: Write a function to convert the given binary tuple to integer.
- 498: Write a python function to find gcd of two positive integers.
- 501: Write a python function to find common divisor between two numbers in a given pair.
- 511: Write a python function to find minimum sum of factors of a given number.
- 518: Write a function to find the square root of a perfect number.
- 520: Write a function to find the lcm of the given array elements.
- 541: Write a function to find if the given number is abundant or not.
- 545: Write a python function to toggle only first and last bits of a given number.
- 547: Write a python function to find the sum of hamming distances of all consecutive numbers from o to n.
- 575: Write a python function to find nth number in a sequence which is not a multiple of a given number.
- 657: Write a python function to find the first digit in factorial of a given number.
- 663: Write a function to find the largest possible value of k such that k modulo x is y.
- 671: Write a python function to set the right most unset bit.
- 681: Write a python function to find the smallest prime divisor of a number.
- 683: Write a python function to check whether the given number can be represented by sum of two squares or not.
- 685: Write a python function to find sum of prime numbers between 1 to n.
- 687: Write a function to find the greatest common divisor (gcd) of two integers by using recursion.
- 692: Write a python function to find the last two digits in factorial of a given number.
- 699: Write a python function to find the minimum number of swaps required to convert one binary string to another.
- 707: Write a python function to count the total set bits from 1 to n.
- 711: Write a python function to check whether the product of digits of a number at even and odd places is equal or not.
- 714: Write a python function to count the number of distinct power of prime factor of given number.
- 768: Write a python function to check for odd parity of a given number.
- 783: Write a function to convert rgb color to hsv color.
- 843: Write a function to find the nth super ugly number from a given prime list of size k using heap queue algorithm.
- 849: Write a python function to find sum of all prime divisors of a given number.
- 851: Write a python function to find sum of inverse of divisors.
- 853: Write a python function to find sum of odd factors of a number.
- 855: Write a python function to check for even parity of a given number.
- 876: Write a python function to find lcm of two positive integers.
- 884: Write a python function to check whether all the bits are within a given range or not.
- 887: Write a python function to check whether the given number is odd or not using bitwise operator.
- 891: Write a python function to check whether the given two numbers have same number of digits or not.
- 903: Write a python function to count the total unset bits from 1 to n.
- 907: Write a function to print the first n lucky numbers.
- 909: Write a function to find the previous palindrome of a specified number.
- 950: Write a function to display sign of the chinese zodiac for given year.
- 955: Write a function to find out, if the given number is abundant.
- 957: Write a python function to get the position of rightmost set bit.
- 958: Write a function to convert an integer into a roman numeral.
- 961: Write a function to convert a roman numeral to an integer.

## Lists and sequence transformations

62 existing tasks and 558 synthetic prompts.

Transform, filter, map, rotate, combine, or reshape lists and sequences.

- 27: Write a python function to remove all digits from a list of strings.
- 41: Write a function to filter even numbers using lambda function.
- 49: Write a function to extract every first or specified element from a given two-dimensional list.
- 117: Write a function to convert all possible convertible elements in the list to float.
- 154: Write a function to extract every specified element from a given two dimensional list.
- 157: Write a function to reflect the run-length encoding from a list.
- 196: Write a function to remove all the tuples with length k.
- 215: Write a function to decode a run-length encoded given list.
- 229: Write a function to re-arrange the elements of the given array so that all negative elements appear before positive ones.
- 304: Write a python function to find element at a given index after number of rotations.
- 313: Write a python function to print positive numbers in a list.
- 317: Write a function to reflect the modified run-length encoding from a list.
- 323: Write a function to re-arrange the given array in alternating positive and negative items.
- 328: Write a function to rotate a given list by specified number of items to the left direction.
- 345: Write a function to find the difference between two consecutive numbers in a given list.
- 358: Write a function to find modulo division of two lists using map and lambda function.
- 361: Write a function to remove empty lists from a given list of lists.
- 378: Write a python function to shift last element to first position in the given list.
- 500: Write a function to concatenate all elements of the given list into a string.
- 503: Write a function to add consecutive numbers of a given list.
- 505: Write a function to move all zeroes to the end of the given array.
- 507: Write a function to remove specific words from a given list.
- 536: Write a function to select the nth items of a list.
- 539: Write a function to create a list containing the power of said number in bases raised to the corresponding number in the index using map function.
- 570: Write a function to remove words from a given list of strings containing a character or string.
- 625: Write a python function to interchange first and last elements in a given list.
- 648: Write a function to exchange the position of every n-th value with (n+1)th value and (n+1)th value with n-th value in a given list.
- 649: Write a python function to calculate the sum of the numbers in a list between the indices of a specified range.
- 665: Write a python function to shift first element to the end of given list.
- 673: Write a python function to convert a list of multiple integers into a single integer.
- 682: Write a function to multiply two lists using map and lambda function.
- 690: Write a function to multiply consecutive numbers of a given list.
- 696: Write a function to zip two given lists of lists.
- 718: Write a function to create a list taking alternate elements from another given list.
- 729: Write a function to add two lists using map and lambda function.
- 815: Write a function to sort the given array without using any sorting algorithm. the given array consists of only 0, 1, and 2.
- 816: Write a function to clear the values of the given tuples.
- 817: Write a function to find numbers divisible by m or n from a list of numbers using lambda function.
- 824: Write a python function to remove even numbers from a given list.
- 825: Write a python function to access multiple elements of specified index from a given list.
- 834: Write a function to generate a square matrix filled with elements from 1 to n raised to the power of 2 in spiral order.
- 847: Write a python function to copy a list from a singleton tuple.
- 852: Write a python function to remove negative numbers from a list.
- 857: Write a function to list out the list of given strings individually using map function.
- 859: Write a function to generate all sublists of a given list.
- 864: Write a function to find palindromes in a given list of strings using lambda function.
- 865: Write a function to print n-times a list using map function.
- 867: Write a python function to add a minimum number such that the sum of array becomes even.
- 869: Write a function to remove sublists from a given list of lists, which are outside a given range.
- 870: Write a function to calculate the sum of the positive numbers of a given list of numbers using lambda function.
- 883: Write a function to find numbers divisible by m and n from a list of numbers using lambda function.
- 889: Write a function to reverse each list in a given list of lists.
- 893: Write a python function to get the last element of each sublist.
- 898: Write a function to extract specified number of elements from a given list, which follow each other continuously.
- 915: Write a function to rearrange positive and negative numbers in a given array using lambda function.
- 919: Write a python function to multiply all items in the list.
- 921: Write a function to perform chunking of tuples each of size n.
- 924: Write a function to find maximum of two numbers.
- 932: Write a function to remove duplicate words from a given list of strings.
- 943: Write a function to combine two given sorted lists using heapq module.
- 972: Write a function to concatenate the given two tuples to a nested tuple.
- 973: Write a python function to left rotate the string.

## Search, sorting, and selection

68 existing tasks and 612 synthetic prompts.

Find elements, indices, ranks, top or bottom values, or sort data.

- 22: Write a function to find the first duplicate element in a given array of integers.
- 23: Write a python function to find the maximum sum of elements of list in a list of lists.
- 31: Write a function to find the top k integers that occur most frequently from given lists of sorted and distinct integers using heap queue algorithm.
- 34: Write a python function to find the missing number in a sorted array.
- 37: Write a function to sort a given mixed list of integers and strings.
- 50: Write a function to find the list with minimum length using lambda function.
- 54: Write a function to sort the given array by using counting sort.
- 121: Write a function to find the triplet with sum of the given array
- 152: Write a function to sort the given array by using merge sort.
- 184: Write a function to find all the values in a list that are greater than a specified number.
- 189: Write a python function to find the first missing positive number.
- 195: Write a python function to find the first position of an element in a sorted array.
- 200: Write a function to find all index positions of the maximum values in a given list.
- 209: Write a function to delete the smallest element from the given heap and then insert a new item.
- 219: Write a function to extract maximum and minimum k elements in the given tuple.
- 221: Write a python function to find the first even number in a given list of numbers.
- 225: Write a python function to find the minimum element in a sorted and rotated array.
- 243: Write a function to sort the given list based on the occurrence of first element of tuples.
- 275: Write a python function to find the position of the last removed element from the given array.
- 316: Write a function to find the index of the last occurrence of a given number in a sorted array.
- 322: Write a function to find all index positions of the minimum values in a given list.
- 333: Write a python function to sort a list according to the second element in sublist.
- 340: Write a python function to find the sum of the three lowest positive numbers from a given list of numbers.
- 366: Write a python function to find the largest product of the pair of adjacent elements from a given list of integers.
- 370: Write a function to sort a tuple by its float element.
- 371: Write a function to find the smallest missing element in a sorted array.
- 372: Write a function to sort a given list of elements in ascending order using heap queue algorithm.
- 381: Write a function to sort a list of lists by a given index of the inner list.
- 382: Write a function to find the number of rotations in a circularly sorted array.
- 393: Write a function to find the list with maximum length using lambda function.
- 408: Write a function to find k number of pairs which consist of one element from the first array and one element from the second array.
- 443: Write a python function to find the largest negative number from the given list.
- 466: Write a function to find the peak element in the given array.
- 485: Write a function to find the largest palindromic number in the given array.
- 487: Write a function to sort a list of tuples in increasing order by the last element in each tuple.
- 492: Write a function to search an element in the given array by using binary search.
- 496: Write a function to find the smallest integers from a given list of numbers using heap queue algorithm.
- 516: Write a function to sort a list of elements using radix sort.
- 517: Write a python function to find the largest postive number from the given list.
- 527: Write a function to find all pairs in an integer array whose sum is equal to a given number.
- 528: Write a function to find the list of lists with minimum length.
- 550: Write a python function to find the maximum element in a sorted and rotated array.
- 627: Write a python function to find the smallest missing number from the given array.
- 656: Write a python function to find the minimum sum of absolute differences of two arrays.
- 672: Write a function to find maximum of three numbers.
- 698: Write a function to sort dictionary items by tuple product of keys for the given dictionary with tuple keys.
- 705: Write a function to sort a list of lists by length and value.
- 795: Write a function to find the n - cheap price items from a given dataset using heap queue algorithm.
- 802: Write a python function to count the number of rotations required to generate a sorted array.
- 829: Write a function to find out the second most repeated (or frequent) string in the given sequence.
- 836: Write a function to find length of the subarray having maximum sum.
- 839: Write a function to sort the tuples alphabetically by the first item of each tuple.
- 841: Write a function to count the number of inversions in the given array.
- 844: Write a python function to find the kth element in an array containing odd elements first and then even elements.
- 856: Write a python function to find minimum adjacent swaps required to sort binary array.
- 861: Write a function to find all anagrams of a string in a given list of strings using lambda function.
- 890: Write a python function to find the index of an extra element present in one sorted array.
- 896: Write a function to sort a list in increasing order by the last element in each tuple from a given list of non-empty tuples.
- 899: Write a python function to check whether an array can be sorted or not by picking only the corner elements.
- 908: Write a function to find the fixed point in the given array.
- 911: Write a function to compute maximum product of three numbers of a given array of integers using heap queue algorithm.
- 916: Write a function to find if there is a triplet in the array whose sum is equal to a given value.
- 922: Write a function to find a pair with the highest product from a given array of integers.
- 938: Write a function to find three closest elements from three sorted arrays.
- 940: Write a function to sort the given array by using heap sort.
- 949: Write a function to sort the given tuple list basis the total digits in tuple.
- 951: Write a function to find the maximum of similar indices in two lists of tuples.
- 970: Write a function to find minimum of two numbers.

## Counting and frequency

50 existing tasks and 450 synthetic prompts.

Count items or compute frequencies, histograms, or simple statistics over collections.

- 13: Write a function to count the most common words in a dictionary.
- 29: Write a python function to find the element occurring odd number of times.
- 40: Write a function to find frequency of the elements in a given list of lists using collections module.
- 42: Write a python function to find the sum of repeated elements in a given array.
- 143: Write a function to find number of lists present in the given tuple.
- 183: Write a function to count all the distinct pairs having a difference of k in any array.
- 204: Write a python function to count the occurrence of a given character in a string.
- 258: Write a function to find number of odd elements in the given list using lambda function.
- 303: Write a python function to check whether the count of inversion of two types are same or not.
- 326: Write a function to get the word with most number of occurrences in the given strings list.
- 329: Write a python function to count negative numbers in a list.
- 332: Write a function to count character frequency of a given string.
- 343: Write a function to calculate the number of digits and letters in a string.
- 351: Write a python function to find the first element occurring k times in a given array.
- 362: Write a python function to find the item with maximum occurrences in a given list.
- 384: Write a python function to find the frequency of the smallest value in a given array.
- 400: Write a function to extract the frequency of unique tuples in the given list order irrespective.
- 442: Write a function to find the ration of positive numbers in an array of integers.
- 461: Write a python function to count the upper case characters in a given string.
- 480: Write a python function to find the maximum occurring character in a given string.
- 489: Write a python function to find the frequency of the largest value in a given array.
- 512: Write a function to count the element frequency in the mixed nested tuple.
- 530: Write a function to find the ration of negative numbers in an array of integers.
- 537: Write a python function to find the first repeated word in a given string.
- 540: Write a python function to find the difference between highest and least frequencies in a given array.
- 658: Write a function to find the item with maximum occurrences in a given list.
- 666: Write a function to count occurrence of a character in a string.
- 684: Write a python function to count occurences of a character in a repeated string.
- 686: Write a function to find the frequency of each element in the given list.
- 697: Write a function to find number of even elements in the given list using lambda function.
- 700: Write a function to count the number of elements in a list which are within a specific range.
- 717: Write a function to calculate the standard deviation.
- 776: Write a function to count those characters which have vowels as their neighbors in the given string.
- 779: Write a function to count the number of unique lists within a list.
- 810: Write a function to iterate over elements repeating each as many times as its count.
- 819: Write a function to count the frequency of consecutive duplicate elements in a given list of numbers.
- 827: Write a function to sum a specific column of a list in a given list of lists.
- 828: Write a function to count alphabets,digits and special charactes in a given string.
- 831: Write a python function to count equal element pairs from the given array.
- 842: Write a function to find the number which occurs for odd number of times in the given array.
- 845: Write a python function to count the number of digits in factorial of a given number.
- 858: Write a function to count number of lists in a given list of lists and square the count.
- 862: Write a function to find the occurrences of n most common words in a given text.
- 881: Write a function to find the sum of first even and odd number of a given list.
- 886: Write a function to add all the numbers in a list and divide it with the length of the list.
- 929: Write a function to count repeated items of a tuple.
- 937: Write a function to count the most common character in a given string.
- 941: Write a function to count the elements in a list until an element is a tuple.
- 946: Write a function to find the most common elements and their counts of a specified text.
- 959: Write a python function to find the average of a list.

## Strings and text processing

77 existing tasks and 693 synthetic prompts.

Split, search, replace, parse, format, or transform strings and text.

- 15: Write a function to split a string at lowercase letters.
- 30: Write a python function to count all the substrings starting and ending with same characters.
- 43: Write a function to find sequences of lowercase letters joined with an underscore using regex.
- 44: Write a function that matches a word at the beginning of a string.
- 73: Write a function to split the given string with multiple delimiters by using regex.
- 83: Write a python function to find the character made by adding all the characters of the given string.
- 146: Write a function to find the ascii value of total characters in a string.
- 173: Write a function to remove everything except alphanumeric characters from a string.
- 178: Write a function to search some literals strings in a string.
- 181: Write a function to find the longest common prefix in the given set of strings.
- 186: Write a function to search some literals strings in a string by using regex.
- 202: Write a function to remove even characters in a string.
- 220: Write a function to replace maximum n occurrences of spaces, commas, or dots with a colon.
- 254: Write a function to find all words starting with 'a' or 'e' in a given string.
- 315: Write a python function to find the first maximum length of even word.
- 319: Write a function to find all five characters long word in the given string by using regex.
- 330: Write a function to find all three, four, five characters long words in the given string by using regex.
- 337: Write a function that matches a word at the end of a string, with optional punctuation.
- 338: Write a python function to count the number of substrings with same first and last characters.
- 350: Write a python function to minimize the length of the string by removing occurrence of only one character.
- 364: Write a function to find the number of flips required to make the given binary string a sequence of alternate characters.
- 377: Write a python function to remove all occurrences of a character in a given string.
- 386: Write a function to find out the minimum no of swaps required for bracket balancing in the given string.
- 411: Write a function to convert the given snake case string to camel case string by using regex.
- 434: Write a function that matches a string that has an a followed by one or more b's.
- 482: Write a function to find sequences of one upper case letter followed by lower case letters in the given string by using regex.
- 495: Write a function to remove lowercase substrings from a given string by using regex.
- 526: Write a python function to capitalize first and last letters of each word of a given string.
- 532: Write a function to check if the two given strings are permutations of each other.
- 534: Write a function to search a literals string in a string and also find the location within the original string where the pattern occurs.
- 542: Write a function to replace all occurrences of spaces, commas, or dots with a colon in the given string by using regex.
- 546: Write a function to find the last occurrence of a character in a string.
- 584: Write a function to find all adverbs and their positions in a given sentence by using regex.
- 595: Write a python function to count minimum number of swaps required to convert one binary string to another.
- 621: Write a function to increment the numeric values in the given strings by k.
- 640: Write a function to remove the parenthesis area in a string.
- 647: Write a function to split a string at uppercase letters.
- 667: Write a python function to count number of vowels in the string.
- 668: Write a python function to replace multiple occurence of character by single.
- 674: Write a function to remove duplicate words from a given string using collections module.
- 676: Write a function to remove everything except alphanumeric characters from the given string by using regex.
- 678: Write a python function to remove spaces from a given string.
- 693: Write a function to remove multiple spaces in a string by using regex.
- 708: Write a python function to convert a string to a list.
- 715: Write a function to convert the given string of integers into a tuple.
- 719: Write a function that matches a string that has an a followed by zero or more b's.
- 727: Write a function to remove all characters except letters and numbers using regex
- 756: Write a function that matches a string that has an a followed by zero or one 'b'.
- 774: Write a function to check if the string is a valid email address or not using regex.
- 812: Write a function to abbreviate 'road' as 'rd.' in a given string.
- 813: Write a function to find length of the string.
- 818: Write a python function to count lower case letters in a given string.
- 823: Write a function to check if the given string starts with a substring using regex.
- 832: Write a function to extract the maximum numeric value from a string by using regex.
- 838: Write a python function to find minimum number swaps required to make two binary strings equal.
- 860: Write a function to check whether the given string is ending with only alphanumeric characters or not using regex.
- 868: Write a python function to find the length of the last word in a given string.
- 871: Write a python function to check whether the given strings are rotations of each other or not.
- 874: Write a python function to check if the string is a concatenation of another string.
- 877: Write a python function to sort the given string.
- 879: Write a function that matches a string that has an 'a' followed by anything, ending in 'b' by using regex.
- 885: Write a python function to check whether the two given strings are isomorphic to each other or not.
- 892: Write a function to remove multiple spaces in a string.
- 897: Write a python function to check whether the word is present in a given sentence or not.
- 900: Write a function where a string will start with a specific number.
- 906: Write a function to extract year, month and date from a url by using regex.
- 913: Write a function to check for a number at the end of a string.
- 914: Write a python function to check whether the given string is made up of two alternating characters or not.
- 917: Write a function to find the sequences of one upper case letter followed by lower case letters.
- 930: Write a function that matches a string that has an a followed by zero or more b's by using regex.
- 933: Write a function to convert camel case string to snake case string by using regex.
- 944: Write a function to separate and print the numbers and their position of a given string.
- 947: Write a python function to find the length of the shortest word.
- 956: Write a function to split the given string at uppercase letters by using regex.
- 964: Write a python function to check whether the length of the word is even or not.
- 965: Write a function to convert camel case string to snake case string.
- 967: Write a python function to accept the strings which contains all vowels.

## Set and membership operations

20 existing tasks and 180 synthetic prompts.

Find duplicates, intersections, subsets, membership, uniqueness, or shared items.

- 25: Write a python function to find the product of non-repeated elements in a given array.
- 46: Write a python function to determine whether all the numbers are different from each other are not.
- 193: Write a function to remove the duplicates from the given tuple.
- 216: Write a function to check if a nested list is a subset of another nested list.
- 249: Write a function to find the intersection of two arrays using lambda function.
- 298: Write a function to find the nested list elements which are present in another list.
- 352: Write a python function to check whether all the characters in a given string are unique.
- 431: Write a function that takes two lists and returns true if they have at least one common element.
- 484: Write a function to remove the matching tuples from the given two tuples.
- 651: Write a function to check if one tuple is a subset of another tuple.
- 659: Write a python function to print duplicants from a list of integers.
- 706: Write a function to find whether an array is subset of another array.
- 712: Write a function to remove duplicates from a list of lists.
- 811: Write a function to check if two lists of tuples are identical or not.
- 872: Write a function to check if a nested list is a subset of another nested list.
- 878: Write a function to check if the given tuple contains only k elements.
- 942: Write a function to check if any list element is present in the given list.
- 945: Write a function to convert the given tuples into set.
- 953: Write a python function to find the minimun number of subsets with distinct elements.
- 966: Write a function to remove an empty tuple from a list of tuples.

## Mappings, tuples, and record aggregation

50 existing tasks and 450 synthetic prompts.

Read, combine, filter, or summarize dictionaries, tuples, and structured records.

- 81: Write a function to zip the two given tuples.
- 114: Write a function to assign frequency to each tuple in the given tuple list.
- 156: Write a function to convert a tuple of string values to a tuple of integer values.
- 174: Write a function to group a sequence of key-value pairs into a dictionary of lists.
- 197: Write a function to perform the exponentiation of the given two tuples.
- 205: Write a function to find the inversions of tuple elements in the given tuple list.
- 206: Write a function to perform the adjacent element concatenation in the given tuples.
- 213: Write a function to perform the concatenation of two string tuples.
- 263: Write a function to merge two dictionaries.
- 307: Write a function to get a colon of a tuple.
- 324: Write a function to extract the sum of alternate chains of tuples.
- 341: Write a function to convert the given set into ordered tuples.
- 357: Write a function to find the maximum element of all the given tuple records.
- 363: Write a function to add the k elements to each element in the tuple.
- 368: Write a function to repeat the given tuple n times.
- 376: Write a function to remove tuple elements that occur more than once and replace the duplicates with some custom value.
- 401: Write a function to perform index wise addition of tuple elements in the given two nested tuples.
- 417: Write a function to find common first element in given list of tuple.
- 438: Write a function to count bidirectional tuple pairs.
- 444: Write a function to trim each tuple by k in the given tuple list.
- 490: Write a function to extract all the pairs which are symmetric in the given tuple list.
- 513: Write a function to convert tuple into list by adding the given string after every element.
- 514: Write a function to find the summation of tuple elements in the given tuple list.
- 533: Write a function to remove particular data type elements from the given tuple.
- 538: Write a python function to convert a given string list to a tuple.
- 544: Write a function to flatten the tuple list to a string.
- 553: Write a function to convert the given tuple to a floating-point number.
- 561: Write a function to assign with each element, its pair elements from other similar pairs in the given tuple.
- 613: Write a function to find the maximum value in record list as tuple attribute in the given tuple list.
- 645: Write a function to find the product of it’s kth index in the given tuples.
- 653: Write a function to group a sequence of key-value pairs into a dictionary of lists using collections module.
- 662: Write a function to sort a list in a dictionary.
- 679: Write a function to access dictionary key’s element by index.
- 691: Write a function to group the 1st elements on the basis of 2nd elements in the given tuple list.
- 694: Write a function to extract unique values from the given dictionary values.
- 709: Write a function to count unique keys for each value present in the tuple.
- 710: Write a function to access the initial and last data of the given tuple record.
- 713: Write a function to check if the given tuple contains all valid values or not.
- 821: Write a function to merge two dictionaries into a single expression.
- 833: Write a function to get dictionary keys as a list.
- 875: Write a function to find the minimum difference in the tuple pairs of given tuples.
- 888: Write a function to substract the elements of the given nested tuples.
- 894: Write a function to convert the given string of float type into tuple.
- 902: Write a function to combine two dictionaries by adding values for common keys.
- 920: Write a function to remove all tuples with all none values in the given tuple list.
- 925: Write a python function to calculate the product of all the numbers of a given tuple.
- 936: Write a function to re-arrange the given tuples based on the given ordered list.
- 939: Write a function to sort a list of dictionaries using lambda function.
- 948: Write a function to get an item of a tuple.
- 969: Write a function to join the tuples if they have similar initial elements.

## Recurrence, combinatorics, and dynamic programming

52 existing tasks and 468 synthetic prompts.

Compute recurrences, count combinations, or optimize a result over choices or subsequences.

- 28: Write a python function to find binomial co-efficient.
- 55: Write a function to find t-nth term of geometric series.
- 60: Write a function to find the maximum length of the subsequence with difference between adjacent elements for the given array.
- 147: Write a function to find the maximum total path sum in the given triangle.
- 149: Write a function to find the longest subsequence such that the difference between adjacents is one for the given array.
- 169: Write a function to calculate the nth pell number.
- 187: Write a function to find the longest common subsequence for the given two sequences.
- 207: Write a function to count the longest repeating subsequences such that the two subsequences don’t have same string characters at same positions.
- 231: Write a function to find the maximum sum in the given right triangle of numbers.
- 291: Write a function to find out the number of ways of painting the fence such that at most 2 adjacent posts have the same color for the given fence with n posts and k colors.
- 314: Write a function to find out the maximum sum such that no two chosen numbers are adjacent for the given rectangular grid of dimension 2 x n.
- 325: Write a python function to find the minimum number of squares whose sum is equal to a given number.
- 346: Write a function to find entringer number e(n, k).
- 348: Write a function to count sequences of given length having non-negative prefix sums that can be generated by given values.
- 360: Write a function to find the n’th carol number.
- 374: Write a function to print all permutations of a given string including duplicates.
- 385: Write a function to find the n'th perrin number using recursion.
- 402: Write a function to compute the value of ncr%p.
- 416: Write a function to find the maximum sum we can make by dividing number in three parts recursively and summing them up together for the given number.
- 423: Write a function to solve gold mine problem.
- 469: Write a function to find the maximum profit earned from a maximum of k stock transactions
- 481: Write a function to determine if there is a subset of the given set with sum equal to the given sum.
- 506: Write a function to calculate the permutation coefficient of given p(n, k).
- 510: Write a function to find the number of subsequences having product smaller than k for the given non negative array.
- 515: Write a function to check if there is a subset with sum divisible by m.
- 522: Write a function to find the longest bitonic subsequence for the given array.
- 524: Write a function to find the sum of maximum increasing subsequence of the given array.
- 529: Write a function to find the nth jacobsthal-lucas number.
- 531: Write a function to find minimum number of coins that make a given value.
- 548: Write a function to find the length of the longest increasing subsequence of the given sequence.
- 571: Write a function to find maximum possible sum of disjoint pairs for the given array of integers and a number k.
- 661: Write a function to find the maximum sum that can be formed which has no three consecutive elements present.
- 689: ## write a function to find the minimum number of jumps to reach the end of the array for the given array of integers where each element represents the max number of steps that can be made forward from that element. > indented block > indented block
- 701: Write a function to find the equilibrium index of the given array.
- 702: Write a function to find the minimum number of elements that should be removed such that amax-amin<=k.
- 704: Write a function to calculate the harmonic sum of n-1.
- 738: Write a function to calculate the geometric sum of n-1.
- 747: Write a function to find the longest common subsequence for the given three string sequence.
- 863: Write a function to find the length of the longest sub-sequence such that elements in the subsequences are consecutive integers.
- 873: Write a function to solve the fibonacci sequence using recursion.
- 895: Write a function to find the maximum sum of subsequences of given array with no adjacent elements.
- 905: Write a python function to find the sum of squares of binomial co-efficients.
- 912: Write a function to find ln, m lobb number.
- 918: Write a function to count coin change.
- 923: Write a function to find the length of the shortest string that has both str1 and str2 as subsequences.
- 926: Write a function to find n-th rencontres number.
- 934: Write a function to find the nth delannoy number.
- 952: Write a function to compute the value of ncr mod p.
- 960: Write a function to solve tiling problem.
- 968: Write a python function to find maximum possible value for the given periodic function.
- 971: Write a function to find the maximum number of segments of lengths a, b and c that can be formed from n.
- 974: Write a function to find the minimum total path sum in the given triangle.

## Matrices and grids

6 existing tasks and 54 synthetic prompts.

Transform or search two-dimensional arrays, grids, or matrices.

- 241: Write a function to generate a 3d array having each element as '*'.
- 353: Write a function to remove a specified column from a given nested list.
- 380: Write a function to generate a two-dimensional array.
- 551: Write a function to extract a specified column from a given nested list.
- 642: Write a function to remove similar rows from the given tuple matrix.
- 652: Write a function to flatten the given tuple matrix into the tuple list with each tuple representing each column.

## Geometry and spatial calculations

38 existing tasks and 342 synthetic prompts.

Compute geometric properties, distances, areas, volumes, or spatial relations.

- 52: Write a function to caluclate area of a parallelogram.
- 76: Write a python function to count the number of squares in a rectangle.
- 112: Write a python function to find the perimeter of a cylinder.
- 153: Write a function to find the vertex of a parabola.
- 163: Write a function to calculate the area of a regular polygon.
- 176: Write a function to find the perimeter of a triangle.
- 180: Write a function to calculate distance between two points using latitude and longitude.
- 185: Write a function to find the focus of a parabola.
- 190: Write a python function to count the number of integral co-ordinates that lie inside a square.
- 198: Write a function to find the largest triangle that can be inscribed in an ellipse.
- 236: Write a python function to count the maximum number of equilateral triangles that can be formed within a given equilateral triangle.
- 318: Write a python function to find the maximum volume of a cuboid with given sum of sides.
- 347: Write a python function to count the number of squares in a rectangle.
- 355: Write a python function to count the number of rectangles in a circle of radius r.
- 356: Write a function to find the third angle of a triangle using two angles.
- 369: Write a function to find the lateral surface area of cuboid
- 373: Write a function to find the volume of a cuboid.
- 379: Write a function to find the surface area of a cuboid.
- 488: Write a function to find the area of a pentagon.
- 493: Write a function to calculate a grid of hexagon coordinates where function returns a list of lists containing 6 tuples of x, y point coordinates.
- 497: Write a function to find the surface area of a cone.
- 499: Write a function to find the diameter of a circle.
- 519: Write a function to calculate volume of a tetrahedron.
- 525: Write a python function to check whether two given lines are parallel or not.
- 535: Write a function to find the top or bottom surface area of a cylinder.
- 574: Write a function to find the surface area of a cylinder.
- 617: Write a function to check for the number of jumps required of given length to reach a point of form (d, 0) from origin in a 2d plane.
- 646: Write a python function to count number of cubes of size k in a cube of size n.
- 654: Write a function to find the perimeter of a rectangle.
- 716: Write a function to find the perimeter of a rombus.
- 746: Write a function to find area of a sector.
- 761: Write a function to caluclate arc length of an angle.
- 789: Write a function to calculate the perimeter of a regular polygon.
- 814: Write a function to find the area of a rombus.
- 835: Write a python function to find the slope of a line.
- 848: Write a function to find the area of a trapezium.
- 850: Write a function to check if a triangle of positive area is possible with the given angles.
- 882: Write a function to caluclate perimeter of a parallelogram.

## Graphs, paths, intervals, and chains

6 existing tasks and 54 synthetic prompts.

Work with connected structures, paths, intervals, ranges, chains, or reachability.

- 110: Write a function to extract the ranges that are missing from the given list with the given start range and end range values.
- 342: Write a function to find the smallest range that includes at-least one element from each of the given arrays.
- 601: Write a function to find the longest chain which can be formed from the given set of pairs.
- 660: Write a python function to choose points from two ranges such that no point lies in both the ranges.
- 846: Write a function to find the minimum number of platforms required for a railway/bus station.
- 927: Write a function to calculate the height of the given binary tree.

## Predicates, validation, and classification

46 existing tasks and 414 synthetic prompts.

Return a Boolean or a category after checking a rule, format, trend, or class.

- 26: Write a function to check if the given tuple list has all k elements.
- 39: Write a function to check if the letters of a given string can be rearranged so that two characters that are adjacent to each other are different.
- 51: Write a function to print check if the triangle is equilateral or not.
- 53: Write a python function to check whether the first and last characters of a given string are equal or not.
- 115: Write a function to check whether all dictionaries in a list are empty or not.
- 134: Write a python function to check whether the last element of given array is even or odd after performing an operation p times.
- 159: Write a function to print the season for the given month and day.
- 175: Write a function to verify validity of a string of parentheses.
- 182: Write a function to find uppercase, lowercase, special character and numeric values using regex.
- 191: Write a function to check whether the given month name contains 30 days or not.
- 192: Write a python function to check whether a string has atleast one letter and one number.
- 201: Write a python function to check whether the elements in a list are same or not.
- 208: Write a function to check the given decimal with a precision of 2 by using regex.
- 210: Write a function to check that the given string contains only a certain set of characters(in this case a-z, a-z and 0-9) by using regex.
- 327: Write a function to print check if the triangle is isosceles or not.
- 334: Write a python function to check whether the triangle is valid or not if sides are given.
- 336: Write a function to check whether the given month name contains 28 days or not.
- 349: Write a python function to check whether the given string is a binary string or not.
- 359: Write a python function to check whether one root of the quadratic equation is twice of the other or not.
- 367: Write a function to check if a binary tree is balanced or not.
- 387: Write a python function to check whether the hexadecimal number is even or odd.
- 396: Write a function to check whether the given string starts and ends with the same character or not using regex.
- 403: Write a function to check if a url is valid or not using regex.
- 449: Write a python function to check whether the triangle is valid or not if 3 points are given.
- 464: Write a function to check if all values are same in a dictionary.
- 508: Write a function to check if the common elements between two given lists are in the same order or not.
- 521: Write a function to print check if the triangle is scalene or not.
- 523: Write a function to check whether a given string has a capital letter, a lower case letter, a number and specified length using lambda function.
- 552: Write a python function to check whether a given sequence is linear or not.
- 582: Write a function to check if a dictionary is empty or not.
- 636: Write a python function to check if roots of a quadratic equation are reciprocal of each other or not.
- 650: Write a python function to check whether the given two arrays are equal or not.
- 669: Write a function to check whether the given ip address is valid or not using regex.
- 670: Write a python function to check whether a sequence of numbers has a decreasing trend or not.
- 677: Write a function to check if the triangle is valid or not.
- 680: Write a python function to check whether a sequence of numbers has an increasing trend or not.
- 695: Write a function to check if each element of the second tuple is greater than its corresponding index in the first tuple.
- 703: Write a function to check whether the given key is present in the dictionary or not.
- 820: Write a function to check whether the given month number contains 28 days or not.
- 822: Write a function to return true if the password is valid.
- 826: Write a python function to find the type of triangle from the given sides.
- 840: Write a python function to check whether the roots of a quadratic equation are numerically equal but opposite in sign or not.
- 854: Write a function which accepts an arbitrary list and converts it to a heap using heap queue algorithm.
- 866: Write a function to check whether the given month name contains 31 days or not.
- 904: Write a function to return true if the given number is even else return false.
- 910: Write a function to validate a gregorian date.
