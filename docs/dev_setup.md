# Development Setup

This document covers a few tips for working on Sonic locally.  See
[README.md](../README.md) for the full installation steps.

## Console Titles

The CLI scripts set the terminal window's title so it is easy to see which
service is running.  This works in `cmd.exe`, PowerShell and Windows Terminal
on Windows, and most macOS/Linux terminals that honour escape sequences.

The title string is chosen in the following order:

1. The `CONSOLE_TITLE` environment variable if it is set.
2. A future command line flag.
3. The hard‑coded default.

Example output on launch:

```
Sonic Launch Pad – backend:5000
```

Set `NO_CONSOLE_TITLE=1` to disable updating the window title.
