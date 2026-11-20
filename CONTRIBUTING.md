# Contributing

## Ground rules for detection rules

Every new deletion target must satisfy all three:

1. **It is provably Tencent/ACE owned.** No guessing from a filename substring alone —
   `ace` matches Windows `spaceparser.sys`. Verify the owning path or registry key.
2. **It has a test.** `tests/test_engine.py` must cover both the positive case and any
   exclusion that protects system or third-party data.
3. **It is reversible in judgment.** Anything that could belong to another application
   (WeChat, QQ, other games) must be excluded explicitly, not by omission.

## Local checks

```bash
python -m py_compile main.py app/*.py tests/*.py
python tests/test_engine.py
python main.py --cli --dry-run     # must never modify the system
```

CI runs the same commands on Windows.

## Style

- Standard library only; no new dependencies without discussion.
- Keep `engine.py` free of Tk imports so it stays testable headless.
- Chinese and English docs are both maintained; update both.