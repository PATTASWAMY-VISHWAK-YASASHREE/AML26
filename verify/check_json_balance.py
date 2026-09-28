"""Locate unbalanced brackets in a JSON file (streaming, no json.load)."""
import sys

path = sys.argv[1]
s = open(path, encoding="utf-8").read()
n = len(s)
stack = []
instr = False
esc = False
pairs = {"]": "[", "}": "{"}
mismatch = None
idx = 0
while idx < n:
    ch = s[idx]
    if instr:
        if esc:
            esc = False
        elif ch == "\\":
            esc = True
        elif ch == '"':
            instr = False
    else:
        if ch == '"':
            instr = True
        elif ch in "[{":
            stack.append((ch, idx))
        elif ch in "]}":
            if not stack or stack[-1][0] != pairs[ch]:
                mismatch = (idx, ch)
                break
            stack.pop()
    idx += 1

if instr:
    print("ERROR: unterminated string starting before char", n)
if mismatch:
    i, ch = mismatch
    print(f"MISMATCH: '{ch}' at char {i} line {s[:i].count(chr(10)) + 1}")
    print("  context:", repr(s[max(0, i - 200):i + 80]))
print("unclosed containers:", len(stack))
for ch, pos in stack:
    line = s[:pos].count("\n") + 1
    print(f"  '{ch}' opened at char {pos}, line {line}")
    print("     context:", repr(s[pos:pos + 160]))
