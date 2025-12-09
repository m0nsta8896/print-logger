# Custom Logger

Version: `2.1.0`

This utility provides a highly configurable, "drop-in" replacement for the Python `print` function. It enables robust, dual-destination logging (console + file) with automatic daily rotation, retention policies, and thread-safe operations. It is designed for production environments where simple `print` debugging is insufficient, but full-scale logging frameworks are overkill.

## Key Features

* **Drop-in Replacement**: Use `print()` exactly as you always have. No syntax changes required.
* **Rich Configuration**: Customize file encodings, buffering, log directory, timestamps, and more.
* **Log Levels**: Includes built-in methods for `print.success()`, `print.warning()`, `print.error()`, `print.debug()`, and `print.critical()`.
* **ANSI Colors**: Automatic color-coded output for the console (fully customizable).
* **Smart Formatting**: Intelligently handles partial line writes (`end=""`) and ensures timestamps are only applied to fresh lines.
* **Stderr Capture**: Automatically hooks into `sys.stderr` to log uncaught exceptions and tracebacks to the file without disrupting console error reporting.
* **Automatic Maintenance**: Rotates log files daily and deletes old logs based on a configurable retention period.

## How to Use

### 1. Import and Initialize

Instantiate the `Config` object with your desired settings, then pass it to the `Print` class.

```python
import pytz
from printlogger import Config, Print

# 1. Define Configuration
config = Config(
    app_name="MyBot",
    logs_dir="logs",
    retention_days=30,
    timezone=pytz.timezone("America/New_York"),
    use_console_colors=True
)

# 2. Create the Logger
print = Print(config)

# Note: To make this custom logger (Print) the default 'print' function
# throughout your entire project (across multiple files), you can overwrite
# the builtins.print function instead:
# ------------------------------
# import builtins
# builtins.print = Print(config)
# ------------------------------
```
### 2. Usage

Once initialized, print behaves like a function but possesses methods for specific log levels.

```python
# Standard usage (Defaults to INFO level)
print("System initializing...")
print("Loading modules", end="...")
print("Done!")  # Appends to the same line in file/console

# Specific Log Levels
print.info("Connecting to database...")
print.success("Database connected successfully.")
print.warning("High latency detected:", "450ms")
print.error("Connection dropped.")
print.critical("System Failure! Shutting down.")
print.debug("Variable state:", {"x": 10, "y": 20})

# Simulating a crash (Captured automatically)
1 / 0
```

### Expected output

The following illustrates the expected console output, showing the timestamp, log level tag, and message. Note how the line writes (end="...") are correctly handled, and the traceback from the simulated crash is captured and logged.

```bash
[13:56:09] [i] System initializing...
[13:56:09] [i] Loading modules...Done!
[13:56:09] [i] Connecting to database...
[13:56:09] [s] Database connected successfully.
[13:56:09] [w] High latency detected: 450ms
[13:56:09] [e] Connection dropped.
[13:56:09] [c] System Failure! Shutting down.
[13:56:09] [d] Variable state: {'x': 10, 'y': 20}
[13:56:09] [e] Traceback (most recent call last):
[13:56:09] [e]   File "/storage/emulated/0/Projects/Logger/2.1.0/example.py", line 41, in <module>
[13:56:09] [e]     1 / 0
[13:56:09] [e]     ~~^~~
[13:56:09] [e] ZeroDivisionError: division by zero
```

## Configuration Reference

The Config class accepts the following parameters:

Parameter            | Type     | Default            | Description                                                             |
:------------------- | :------- | :----------------- | :---------------------------------------------------------------------- |
CORE SETTINGS        |          |                    |                                                                         |
logs_dir             | str      | "logs"             | Directory path where log files will be stored. Created automatically.   |
timezone             | timezone | UTC                | The timezone used for file rotation and line timestamps.                |
retention_days       | int      | 7                  | Log files older than this will be deleted on startup.                   |
FILE I/O             |          |                    |                                                                         |
log_to_file          | bool     | True               | If False, no files will be created or written to.                       |
file_encoding        | str      | "utf-8"            | Encoding used for log files.                                            |
file_encoding_errors | str      | "replace"          | Strategy for encoding errors (e.g., 'strict', 'ignore').                |
file_buffering       | int      | 1                  | File buffer size. 1 indicates line-buffered.                            |
CONSOLE OUTPUT       |          |                    |                                                                         |
log_to_console       | bool     | True               | If False, output is silenced in the console (but still logged to file). |
use_console_colors   | bool     | True               | Enables ANSI color codes for console output.                            |
capture_stderr       | bool     | True               | Hooks sys.stderr to log exceptions/tracebacks to file.                  |
FORMATTING           |          |                    |                                                                         |
filename_fmt         | str      | "log_%Y-%m-%d.txt" | Format string for daily log filenames.                                  |
timestamp_fmt        | str      | "%H:%M:%S"         | Format string for the timestamp prefix on every line.                   |
TAGS                 |          |                    |                                                                         |
tag_info             | str      | "[INFO]"           | Tag prefixed to standard print() calls.                                 |
tag_error            | str      | "[ERROR]"          | Tag prefixed to print.error() calls.                                    |
tag_warning          | str      | "[WARN]"           | Tag prefixed to print.warning() calls.                                  |
tag_success          | str      | "[SUCCESS]"        | Tag prefixed to print.success() calls.                                  |
tag_debug            | str      | "[DEBUG]"          | Tag prefixed to print.debug() calls.                                    |
tag_critical         | str      | "[CRIT]"           | Tag prefixed to print.critical() calls.                                 |

## Advanced Customization

### Changing Colors

You can modify the ANSI color codes by passing a dictionary to the colors parameter in Config.

```python
config = Config(
    colors={
        "normal": "\033[37m",           # White/Light Gray foreground color
        "info": "\033[34m",             # Blue foreground color
        "error": "\033[31m",            # Red foreground color
        "warning": "\033[33m",          # Yellow foreground color
        "success": "\033[32m",          # Green foreground color
        "debug": "\033[36m",            # Cyan foreground color
        "critical": "\033[41m\033[37m", # White/Light Gray foreground on Red background
        "reset": "\033[0m"              # Reset all formatting/colors to default
    }
    # All your other configurations...
)
```

### Shutdown

The logger automatically registers an atexit handler to close files safely. However, if you need to manually shut it down (e.g., during a restart sequence), you can call:

```python
print.shutdown()
```

## Installation

You can install this package the following command:

```bash
pip install git+https://github.com/m0nsta8896/print-logger.git
```
