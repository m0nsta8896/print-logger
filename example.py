import pytz
import builtins
from printlogger import Config, Print

builtins.print = Print(Config(
    filename_fmt = "%B_%d-%y.log",
    
    tag_info = "[i]",
    tag_error = "[e]",
    tag_warning = "[w]",
    tag_success = "[s]",
    tag_debug = "[d]",
    tag_critical = "[c]",
    
    colors={
        "normal": "\033[37m",
        "info": "\033[34m",
        "error": "\033[31m",
        "warning": "\033[33m",
        "success": "\033[32m",
        "debug": "\033[36m",
        "critical": "\033[41m\033[37m",
        "reset": "\033[0m"
    }
))

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
