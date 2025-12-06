import pytz
from printlogger import Config, Print

# 1. Define Configuration
config = Config(
    app_name="MyBot",
    logs_dir="logs",
    retention_days=30,
    timezone=pytz.timezone("America/New_York"),
    use_console_colors=True,
    colors={
        "info": "\033[37m",     # White
        "error": "\033[91m",    # Light Red
        "success": "\033[92m",  # Light Green
        "warning": "\033[93m",  # Light Yellow
        "debug": "\033[90m",    # Dark Gray
        "critical": "\033[41m", # Red Background
        "reset": "\033[0m"      # Reset
    }
)

# 2. Create the Logger
print = Print(config)

# Standard usage (Defaults to INFO level)
print("System initializing...")
print("Loading modules", end="...")
print("Done!")  # Appends to the same line in file/console

# Specific Log Levels
print.success("Database connected successfully.")
print.warning("High latency detected:", "450ms")
print.error("Connection dropped.")
print.critical("System Failure! Shutting down.")
print.debug("Variable state:", {"x": 10, "y": 20})

# Simulating a crash (Captured automatically)
1 / 0