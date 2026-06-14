# CanMV MicroPython Compatibility

Use this reference before generating a ready-to-copy `main.py` for K230 CanMV.

## Conservative Syntax

CanMV MicroPython may accept a smaller or different Python syntax subset than desktop Python. A script can pass desktop `python -m py_compile` and still fail in CanMV IDE K230 with `SyntaxError: invalid syntax`.

For final scripts, prefer plain MicroPython style:

- Avoid f-strings unless the target firmware has already been tested with them.
- Avoid `lambda`, list comprehensions, dict comprehensions, set comprehensions, and generator expressions in final examples.
- Avoid deeply nested inline expressions.
- Avoid complex multi-line function calls for debug printing, logging, or string formatting.
- Prefer simple loops, temporary variables, and one statement per line.
- Prefer `%` formatting or simple string concatenation for runtime status text.
- Keep `try`/`except` blocks simple and use `print("error:", e)` instead of `sys.print_exception(e)` unless the firmware confirms support.

## Validation Rule

Desktop syntax checks are useful but not sufficient:

```text
python -m py_compile script.py
```

This only proves desktop Python syntax. When hardware is available, also run the script through CanMV IDE or `scripts/run_canmv_raw_repl.py`.

## Template Rule

When generating or editing `assets/contest-template/` files, write them in conservative CanMV style even if desktop Python accepts newer or denser syntax.
