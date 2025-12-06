import os
import sys
import datetime
import threading
import atexit
from dataclasses import dataclass, field
from typing import Optional, TextIO, Dict, Any
@dataclass
class Config:
    """
    Central configuration container for the Print logger.
    This class manages all settings related to file paths, formatting, rotation policies,
    and console output styles. It automatically handles the initialization of the 
    logs directory and cleanup of old files upon instantiation.
    """
    app_name: str = "Application"
    logs_dir: str = "logs"
    timezone: datetime.timezone = datetime.timezone.utc
    retention_days: int = 7
    log_to_file: bool = True
    file_encoding: str = "utf-8"
    file_encoding_errors: str = "replace"
    file_buffering: int = 1
    
    log_to_console: bool = True
    use_console_colors: bool = True
    capture_stderr: bool = True
    
    filename_fmt: str = "log_%Y-%m-%d.txt"
    timestamp_fmt: str = "%H:%M:%S"
    
    tag_debug: str = "[DEBUG]"
    tag_info: str = "[INFO]"
    tag_success: str = "[SUCCESS]"
    tag_warning: str = "[WARN]"
    tag_error: str = "[ERROR]"
    tag_critical: str = "[CRIT]"
    
    colors: Dict[str, str] = field(default_factory=lambda: {
        "debug": "\033[36m",   # Cyan
        "info": "\033[0m",     # Reset/Default
        "success": "\033[32m", # Green
        "warning": "\033[33m", # Yellow
        "error": "\033[31m",   # Red
        "critical": "\033[41m\033[37m", # White on Red Background
        "reset": "\033[0m"
    })
    
    def __post_init__(self):
        """
        Validates configuration and performs initial setup.
        Creates the log directory if it does not exist and triggers the cleanup
        of old log files based on the retention policy.
        """
        if self.log_to_file:
            try:
                os.makedirs(self.logs_dir, exist_ok=True)
                self._cleanup_old_logs()
            except OSError:
                sys.stderr.write(f"Warning: Could not create logs directory '{self.logs_dir}'.\n")
    
    def _cleanup_old_logs(self):
        """
        Scans the logs directory and removes files older than `retention_days`.
        This method is exception-safe and will silently skip files it cannot access.
        """
        if not os.path.exists(self.logs_dir):
            return
        now = datetime.datetime.now(self.timezone)
        cutoff_date = now.date() - datetime.timedelta(days=self.retention_days)
        
        try:
            with os.scandir(self.logs_dir) as entries:
                for entry in entries:
                    if entry.is_file():
                        try:
                            mod_time = entry.stat().st_mtime
                            file_date = datetime.datetime.fromtimestamp(mod_time, self.timezone).date()
                            if file_date < cutoff_date:
                                os.remove(entry.path)
                        except OSError:
                            continue
        except OSError:
            pass
    
    def get_log_filepath(self, date_obj: datetime.date) -> str:
        """
        Generates the full file path for a log file based on the provided date object
        and the configured `filename_fmt`.
        """
        return os.path.join(self.logs_dir, date_obj.strftime(self.filename_fmt))

class Print:
    """
    A drop-in replacement for the built-in print function with advanced logging capabilities.
    This class supports file rotation, thread safety, stderr capture, and custom
    log levels (debug, warning, error, success, critical). It is designed to be
    callable directly to mimic standard print behavior.
    """
    def __init__(self, config: Config):
        """
        Initialize the Print logger with a Config object.
        Args:
            config (Config): The configuration object containing all settings.
        """
        self.config = config
        self._lock = threading.Lock()
        self._current_date = datetime.datetime.now(self.config.timezone).date()
        self._log_file: Optional[TextIO] = None
        self._fresh_line = True
        self._stdout = sys.stdout
        self._stderr = sys.stderr
        if self.config.log_to_file:
            self._rotate_log(force=True)
            atexit.register(self.shutdown)
        if self.config.capture_stderr:
            sys.stderr = self._StderrInterceptor(self)
    
    def __call__(self, *objects, sep: str = ' ', end: str = '\n', file=None, flush: bool = False):
        """
        Standard print implementation. Logs as INFO by default (or standard output).
        Args:
            *objects: Objects to print.
            sep (str): Separator between objects. Defaults to ' '.
            end (str): String appended after the last object. Defaults to '\n'.
            file: A file-like object (stream); defaults to the current sys.stdout.
            flush (bool): Whether to forcibly flush the stream.
        """
        self._generic_log(
            objects, 
            sep=sep, 
            end=end, 
            file=file, 
            flush=flush, 
            tag=self.config.tag_info, 
            color_key="info"
        )
    
    def debug(self, *objects, sep: str = ' ', end: str = '\n'):
        """Logs a message with the DEBUG tag and associated color."""
        self._generic_log(objects, sep, end, tag=self.config.tag_debug, color_key="debug")
    
    def success(self, *objects, sep: str = ' ', end: str = '\n'):
        """Logs a message with the SUCCESS tag and associated color."""
        self._generic_log(objects, sep, end, tag=self.config.tag_success, color_key="success")
    
    def warning(self, *objects, sep: str = ' ', end: str = '\n'):
        """Logs a message with the WARNING tag and associated color."""
        self._generic_log(objects, sep, end, tag=self.config.tag_warning, color_key="warning")
    
    def error(self, *objects, sep: str = ' ', end: str = '\n'):
        """
        Logs a message with the ERROR tag and associated color. 
        Forces a flush to console to ensure immediate visibility of errors.
        """
        self._generic_log(objects, sep, end, flush=True, tag=self.config.tag_error, color_key="error")
    
    def critical(self, *objects, sep: str = ' ', end: str = '\n'):
        """
        Logs a message with the CRITICAL tag and associated color.
        Forces a flush to console.
        """
        self._generic_log(objects, sep, end, flush=True, tag=self.config.tag_critical, color_key="critical")
    
    def _generic_log(self, objects, sep, end, file=None, flush=False, tag="", color_key="info"):
        """
        Internal driver method that handles the formatting, coloring, and dispatching
        of messages to both the console (stdout) and the rotating log file.
        """
        message = sep.join(map(str, objects)) + end
        target_stream = file if file else self._stdout
        
        with self._lock:
            if self.config.log_to_console or file:
                try:
                    out_msg = message
                    if self.config.use_console_colors and file is None:
                        color_code = self.config.colors.get(color_key, "")
                        reset_code = self.config.colors.get("reset", "")
                        out_msg = f"{color_code}{message}{reset_code}"
                    target_stream.write(out_msg)
                    if flush:
                        target_stream.flush()
                except Exception:
                    pass
            
            if self.config.log_to_file and file is None:
                self._write_to_file(message, tag=tag)
    
    def _write_to_file(self, text: str, tag: str):
        """
        Writes text to the managed log file. Handles:
        - Automatic file rotation if the date changes.
        - Timestamp injection at the start of new lines.
        - Tag injection.
        - Buffer state management (handling partial lines via end="").
        """
        if not text:
            return
        self._rotate_log()
        if self._log_file and not self._log_file.closed:
            def get_preamble():
                ts = datetime.datetime.now(self.config.timezone).strftime(self.config.timestamp_fmt)
                return f"[{ts}] {tag} "
            buffer = ""
            parts = text.split('\n')
            has_trailing_newline = text.endswith('\n')
            count = len(parts)
            for i, part in enumerate(parts):
                if i == count - 1 and has_trailing_newline and part == '':
                    continue
                if self._fresh_line:
                    buffer += get_preamble()
                    self._fresh_line = False
                buffer += part
                is_last_part = (i == count - 1)
                if not is_last_part:
                    buffer += "\n"
                    self._fresh_line = True
                elif has_trailing_newline:
                    buffer += "\n"
                    self._fresh_line = True
            try:
                self._log_file.write(buffer)
                self._log_file.flush()
            except Exception:
                pass
    
    def _rotate_log(self, force: bool = False):
        """
        Checks if the current date has changed relative to the open log file.
        If changed, closes the old file and opens a new one.
        """
        now = datetime.datetime.now(self.config.timezone)
        today = now.date()
        if force or today != self._current_date or self._log_file is None:
            self._current_date = today
            if self._log_file:
                try:
                    self._log_file.close()
                except Exception:
                    pass
            try:
                path = self.config.get_log_filepath(today)
                self._log_file = open(
                    path, 
                    "a", 
                    encoding=self.config.file_encoding, 
                    errors=self.config.file_encoding_errors,
                    buffering=self.config.file_buffering
                )
            except OSError:
                self._log_file = None
    
    def shutdown(self):
        """
        Cleanly closes the file handle and restores stderr.
        Should be called on application exit.
        """
        if self._log_file:
            try:
                self._log_file.close()
            except Exception:
                pass
            self._log_file = None
        if isinstance(sys.stderr, self._StderrInterceptor):
            sys.stderr = self._stderr
    
    class _StderrInterceptor:
        """
        A helper class that wraps sys.stderr.
        It captures writes (usually exceptions/tracebacks), buffers them until
        a newline is encountered to ensure atomic log entries, and passes them
        to the logger while also printing to the real stderr.
        """
        def __init__(self, logger_instance):
            self.logger = logger_instance
            self.original_stderr = logger_instance._stderr
            self.buffer = ""
        
        def write(self, message):
            self.original_stderr.write(message)
            self.buffer += message
            while '\n' in self.buffer:
                line, self.buffer = self.buffer.split('\n', 1)
                full_line = line + "\n"
                with self.logger._lock:
                    if self.logger.config.log_to_file:
                        self.logger._write_to_file(full_line, tag=self.logger.config.tag_error)
        
        def flush(self):
            self.original_stderr.flush()
            if self.buffer:
                with self.logger._lock:
                    if self.logger.config.log_to_file:
                        self.logger._write_to_file(self.buffer, tag=self.logger.config.tag_error)
                self.buffer = ""