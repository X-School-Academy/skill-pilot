---
title: "Sorting Numbers in Five Languages"
slug: sorting-numbers-five-languages
type: interactive_tutorial
duration: 25 minutes
id: 2
token: sort-five-langs
---

#### Objectives:

* See how the same idea — sorting a list of integers — is expressed in five popular languages
* Get an intuition for the syntax differences between dynamic and statically-typed languages
* Try each snippet live, modify it, and re-run

Sorting is one of the first algorithms every developer touches. Almost every language ships a built-in sort, so you rarely write the algorithm yourself — you just call it. In this tutorial we'll look at five languages, run a working snippet for each, and call out the small details that change.

## 1. Python

Python is dynamically typed and ships `sorted()` (returns a new list) and `list.sort()` (sorts in place). Both default to ascending order; pass `reverse=True` to flip.

```python {type:code, action: run}
nums = [5, 2, 9, 1, 7, 3]
print(sorted(nums))
print(sorted(nums, reverse=True))
```

## 2. JavaScript

JavaScript's `Array.prototype.sort()` sorts **strings** by default — even when the array contains numbers. To sort numbers correctly you must supply a comparator.

```javascript {type:code, action: run}
const nums = [5, 2, 9, 1, 7, 3];
console.log([...nums].sort());                  // lexicographic — wrong for numbers
console.log([...nums].sort((a, b) => a - b));   // numeric ascending
```

## 3. Go

Go uses the `sort` package. `sort.Ints` sorts a slice of `int` in place. There is no return value — the slice is mutated.

```go {type:code, action: run}
package main

import (
	"fmt"
	"sort"
)

func main() {
	nums := []int{5, 2, 9, 1, 7, 3}
	sort.Ints(nums)
	fmt.Println(nums)
}
```

## 4. Java

Java's `Arrays.sort()` sorts a primitive `int[]` in place using a dual-pivot quicksort.

```java {type:code, action: run}
import java.util.Arrays;

public class Main {
  public static void main(String[] args) {
    int[] nums = {5, 2, 9, 1, 7, 3};
    Arrays.sort(nums);
    System.out.println(Arrays.toString(nums));
  }
}
```

## 5. Rust

Rust's `Vec<T>::sort()` sorts in place, requires `T: Ord`, and is a stable sort. For an unstable but slightly faster variant, use `sort_unstable()`.

```rust {type:code, action: run}
fn main() {
    let mut nums = vec![5, 2, 9, 1, 7, 3];
    nums.sort();
    println!("{:?}", nums);
}
```

## Side-by-side: ascending vs descending

Most languages take a comparator or a flag. Here are two equivalent variants for each language — flip between the tabs to compare.

```tabs {rawCode: true}

\```python {title: "Python"}
nums = [5, 2, 9, 1, 7, 3]
print(sorted(nums))
print(sorted(nums, reverse=True))
\```

\```javascript {title: "JavaScript"}
const nums = [5, 2, 9, 1, 7, 3];
console.log([...nums].sort((a, b) => a - b));
console.log([...nums].sort((a, b) => b - a));
\```

\```go {title: "Go"}
package main
import ("fmt"; "sort")
func main() {
    nums := []int{5, 2, 9, 1, 7, 3}
    sort.Ints(nums)
    fmt.Println(nums)
    sort.Sort(sort.Reverse(sort.IntSlice(nums)))
    fmt.Println(nums)
}
\```

\```java {title: "Java"}
import java.util.*;
public class Main {
  public static void main(String[] args) {
    Integer[] nums = {5, 2, 9, 1, 7, 3};
    Arrays.sort(nums);
    System.out.println(Arrays.toString(nums));
    Arrays.sort(nums, Collections.reverseOrder());
    System.out.println(Arrays.toString(nums));
  }
}
\```

```

#### Summary

Sorting is one of the friendliest places to compare languages because every language hands you the same primitive — yet the surface differs:

* **Python** returns a sorted copy unless you call `.sort()` in place.
* **JavaScript** sorts as strings by default — always pass a comparator for numbers.
* **Go** mutates the slice and returns nothing.
* **Java** sorts primitive arrays in place and gives you a separate path for object arrays.
* **Rust** is in place, stable, and demands the element type implement `Ord`.

If you'd like to explore further, here are some prompts you can ask AI:

```yml-list {default: true}
- How do I sort a list of dictionaries by a key in Python?
- How do I make Array.sort stable for objects in JavaScript?
- How do I do a custom comparator with sort.Slice in Go?
- How do I sort a List<Person> by name in Java?
- What is the difference between sort and sort_unstable in Rust?
```
