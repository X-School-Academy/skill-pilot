# Detect Number

Use this action when a workflow test node needs to inspect text for numeric characters.

## Steps

### Step 1: Read the Input

Read the user-provided string. Treat the full provided text as the input unless the user clearly marks a specific substring to inspect.

### Step 2: Inspect for Numbers

Check whether the input contains numeric characters (`0` through `9`).

### Step 3: Return the Result

If numeric characters are present, return the digits in the same order as a plain-text string.

If no numeric characters are present, return:

`string`

## Expected Output

Output result as plain text. If the user asked to save it to a file, write it there.

- The extracted digits as a plain-text string when digits exist.
- `string` when the input contains no digits.
