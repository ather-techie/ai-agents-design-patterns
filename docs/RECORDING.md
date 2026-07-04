# Recording the demo GIF

`README.md` has a commented-out slot for an animated trace:

```markdown
![ReAct trace](docs/react-trace.gif)
```

To produce `docs/react-trace.gif`:

1. **Get a POSIX terminal.** `asciinema` records via a pty, which native Windows `conhost`/PowerShell doesn't expose. Use WSL, macOS, or Linux.
2. **Install the tools:**
   ```bash
   pip install asciinema
   # agg (asciicast -> gif) is a separate binary, install via cargo or a prebuilt release:
   # https://github.com/asciinema/agg
   ```
3. **Record the ReAct demo:**
   ```bash
   asciinema rec docs/react-trace.cast -c "make demo"
   ```
4. **Convert to GIF:**
   ```bash
   agg docs/react-trace.cast docs/react-trace.gif
   ```
5. **Trim/tune** — keep it under ~15s and under a few MB; `agg --speed 1.5` or `--cols`/`--rows` can help keep it compact and readable when embedded in the README.
6. **Uncomment** the `![ReAct trace](docs/react-trace.gif)` line in `README.md` and delete the placeholder comment above it.
