```yaml {"type":"meta"}
title: "Python Lists: A Hands-On Mini Challenge"
slug: python-lists-mini-challenge
type: guided_challenge
duration: 20 minutes
id: 1
token: py-lists-mini
```

```markdown {"during":1000}
# Python Lists — Mini Challenge

By the end of this short challenge you will be able to:

1. Create a Python list and read items by index
2. Append, insert, and remove items
3. Iterate a list with a `for` loop
4. Pass a quick quiz to confirm what you learned

Take your time. Each step gates on the one before it.
```

```markdown {"type":"control","action":"continue","timeLeft":0}
Ready? Click Continue.
```

```markdown {"during":1000}
## Section 1 — Create and read

A Python list is an ordered, mutable collection. Indices start at `0`:

\```python
fruits = ["apple", "banana", "cherry"]
print(fruits[0])   # apple
print(fruits[-1])  # cherry (negative indices count from the end)
\```
```

```python {"type":"code","action":"run","button":"Run"}
fruits = ["apple", "banana", "cherry"]
print(fruits[0])
print(fruits[-1])
print(len(fruits))
```

```markdown {"type":"control","action":"continue","timeLeft":0}
```

```markdown {"during":1000}
## Section 2 — Modify

- `append(x)` adds `x` at the end.
- `insert(i, x)` inserts `x` at index `i`.
- `remove(x)` removes the first occurrence of `x`.
- `pop(i)` removes and returns the item at index `i` (default: last).
```

```python {"type":"code","action":"run","button":"Run"}
fruits = ["apple", "banana", "cherry"]
fruits.append("date")
fruits.insert(1, "blueberry")
fruits.remove("banana")
last = fruits.pop()
print(fruits)
print("popped:", last)
```

```markdown {"type":"control","action":"continue","timeLeft":0}
```

```yaml {"type":"form","ref":"ask"}
- type: radio
  name: q_index
  label: What does `fruits[-1]` return for `fruits = ["a", "b", "c"]`?
  options:
    - "a"
    - "b"
    - "c"
    - An error
  hint: |
    Negative indices count from the end of the list.
    `-1` is the last element.
  value: 2
```

```markdown {"during":1000}
## Section 3 — Iterate

Use `for item in list:` to walk a list one item at a time:

\```python
for fruit in ["apple", "banana", "cherry"]:
    print(fruit.upper())
\```
```

```python {"type":"code","action":"run","button":"Run"}
for fruit in ["apple", "banana", "cherry"]:
    print(fruit.upper())
```

```markdown {"type":"control","action":"continue","timeLeft":0}
```

```yaml {"type":"form","ref":"ask","row":false}
- type: checkbox
  name: q_methods
  label: "Which of these list methods MODIFY the list in place? (Select all that apply.)"
  options:
    - append
    - insert
    - len
    - remove
    - sorted
  hint: |
    `len` returns a number. `sorted` returns a NEW list.
    The others mutate the original list.
  value: [0, 1, 3]
```

```memory-card {"title":"Python list cheat sheet","cardMinHeight":180}
cards:
  - front: |
      How do you create a list of three numbers?
    back: |
      \```python
      nums = [1, 2, 3]
      \```
  - front: |
      How do you get the last item of a list `xs`?
    back: |
      \```python
      xs[-1]
      \```
  - front: |
      How do you add `9` to the end of a list `xs`?
    back: |
      \```python
      xs.append(9)
      \```
  - front: |
      How do you loop over a list `xs` and print each item?
    back: |
      \```python
      for x in xs:
          print(x)
      \```
```

```markdown {"type":"control","action":"submit","timeLeft":0}
```

```markdown {"type":"control","action":"end"}
🎉 Nice work — you've covered the four core list operations and earned the recall cards. Reuse this pattern next time you meet a new data type.
```
