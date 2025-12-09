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
    Central configuration container for the Print logger application.
    
    This class defines all behavioral settings, including file paths, log retention policies,
    formatting styles, and color definitions. It also handles the initialization of the 
    storage directory and cleanup of expired logs upon instantiation.
    
    Attributes:
        CORE SETTINGS
        logs_dir (str): Directory path where log files will be stored. Created automatically.
        timezone (datetime.timezone): The timezone used for file rotation and line timestamps.
        retention_days (int): Log files older than this will be deleted on startup.
        
        FILE I/O
        log_to_file (bool): If False, no files will be created or written to.
        file_encoding (str): Encoding used for log files.
        file_encoding_errors (str): Strategy for encoding errors (e.g., 'strict', 'ignore').
        file_buffering (int): File buffer size. 1 indicates line-buffered.
        
        CONSOLE OUTPUT
        log_to_console (bool): If False, output is silenced in the console (but still logged to file).
        use_console_colors (bool): Enables ANSI color codes for console output.
        capture_stderr (bool): Hooks sys.stderr to log exceptions/tracebacks to file.
        
        FORMATTING
        filename_fmt (str): Format string for daily log filenames.
        timestamp_fmt (str): Format string for the timestamp prefix on every line.
        
        TAGS
        tag_info (str): Tag prefixed to standard print() calls.
        tag_error (str): Tag prefixed to print.error() calls.
        tag_warning (str): Tag prefixed to print.warning() calls.
        tag_success (str): Tag prefixed to print.success() calls.
        tag_debug (str): Tag prefixed to print.debug() calls.
        tag_critical (str): Tag prefixed to print.critical() calls.
        
        colors (Dict[str, str]): Dictionary mapping log levels to ANSI color codes.
    """
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
    
    tag_info: str = "[INFO]"
    tag_error: str = "[ERROR]"
    tag_warning: str = "[WARN]"
    tag_success: str = "[SUCCESS]"
    tag_debug: str = "[DEBUG]"
    tag_critical: str = "[CRIT]"
    
    colors: Dict[str, str] = field(default_factory=lambda: {
        "normal": "\033[37m",           # White/Light Gray foreground color
        "info": "\033[34m",             # Blue foreground color
        "error": "\033[31m",            # Red foreground color
        "warning": "\033[33m",          # Yellow foreground color
        "success": "\033[32m",          # Green foreground color
        "debug": "\033[36m",            # Cyan foreground color
        "critical": "\033[41m\033[37m", # White/Light Gray foreground on Red background
        "reset": "\033[0m"              # Reset all formatting/colors to default
    })
    
    def __post_init__(self) -> None:
        """
        Performs post-initialization setup.
        
        Creates the logging directory if it does not exist and triggers the cleanup
        process for old log files if logging to file is enabled.
        """
        if self.log_to_file:
            try:
                os.makedirs(self.logs_dir, exist_ok=True)
                self._cleanup_old_logs()
            except OSError:
                sys.stderr.write(f"Warning: Could not create logs directory '{self.logs_dir}'.\n")
    
    def _cleanup_old_logs(self) -> None:
        """
        Removes log files that are older than the specified retention period.
        
        Iterates through files in the configured logs directory, checks their modification
        timestamps, and deletes those exceeding the retention_days threshold relative
        to the current server date.
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
        Generates the full file path for a log file based on a specific date.
        
        Args:
            date_obj (datetime.date): The date for which to generate the filename.
        
        Returns:
            str: The full path to the log file.
        """
        return os.path.join(self.logs_dir, date_obj.strftime(self.filename_fmt))

class Print:
    """
    A thread-safe, drop-in replacement for the built-in print function with advanced logging capabilities.
    
    This class handles message dispatching to both standard output (console) and rotating
    log files. It supports ANSI coloring, timestamping, log level tagging, and optional
    interception of standard error.
    """
    
    def __init__(self, config: Config):
        """
        Initialize the Print logger.
        
        Args:
            config (Config): The configuration object containing logging settings.
        """
        self.config = config
        self._lock = threading.Lock()
        self._current_date = datetime.datetime.now(self.config.timezone).date()
        self._log_file: Optional[TextIO] = None
        self._fresh_line = True
        self._last_entry_pos = 0
        self._stdout = sys.stdout
        self._stderr = sys.stderr
        
        if self.config.log_to_file:
            self._rotate_log(force=True)
            atexit.register(self.shutdown)
        
        if self.config.capture_stderr:
            sys.stderr = self._StderrInterceptor(self)
    
    def __call__(
        self,
        *objects: Any,
        sep: str = ' ',
        end: str = '\n',
        file: Optional[TextIO] = None,
        flush: bool = False
    ) -> None:
        """
        Standard print implementation serving as the default logging method (Info/Normal level).
        
        Args:
            *objects: Objects to print.
            sep (str): Separator between objects.
            end (str): String appended after the last object.
            file (Optional[TextIO]): A file-like object (stream); defaults to current sys.stdout.
            flush (bool): Whether to forcibly flush the stream.
        """
        self._generic_log(
            objects,
            sep, end,
            file, flush,
            tag=self.config.tag_info,
            color_key="normal"
        )
    
    def info(
        self,
        *objects: Any,
        sep: str = ' ',
        end: str = '\n',
        file: Optional[TextIO] = None,
        flush: bool = False
    ) -> None:
        """
        Logs a message with the INFO tag and associated color configuration.
        """
        self._generic_log(
            objects,
            sep, end,
            file, flush,
            tag=self.config.tag_info,
            color_key="info"
        )
    
    def error(
        self,
        *objects: Any,
        sep: str = ' ',
        end: str = '\n',
        file: Optional[TextIO] = None,
        flush: bool = True
    ) -> None:
        """
        Logs a message with the ERROR tag and associated color configuration.
        Defaults to flush=True to ensure errors are recorded immediately.
        """
        self._generic_log(
            objects,
            sep, end,
            file, flush,
            tag=self.config.tag_error,
            color_key="error"
        )
    
    def warning(
        self,
        *objects: Any,
        sep: str = ' ',
        end: str = '\n',
        file: Optional[TextIO] = None,
        flush: bool = False
    ) -> None:
        """
        Logs a message with the WARNING tag and associated color configuration.
        """
        self._generic_log(
            objects,
            sep, end,
            file, flush,
            tag=self.config.tag_warning,
            color_key="warning"
        )
    
    def success(
        self,
        *objects: Any,
        sep: str = ' ',
        end: str = '\n',
        file: Optional[TextIO] = None,
        flush: bool = False
    ) -> None:
        """
        Logs a message with the SUCCESS tag and associated color configuration.
        """
        self._generic_log(
            objects,
            sep, end,
            file, flush,
            tag=self.config.tag_success,
            color_key="success"
        )
    
    def debug(
        self,
        *objects: Any,
        sep: str = ' ',
        end: str = '\n',
        file: Optional[TextIO] = None,
        flush: bool = False
    ) -> None:
        """
        Logs a message with the DEBUG tag and associated color configuration.
        """
        self._generic_log(
            objects,
            sep, end,
            file, flush,
            tag=self.config.tag_debug,
            color_key="debug"
        )
    
    def critical(
        self,
        *objects: Any,
        sep: str = ' ',
        end: str = '\n',
        file: Optional[TextIO] = None,
        flush: bool = True
    ) -> None:
        """
        Logs a message with the CRITICAL tag and associated color configuration.
        Defaults to flush=True.
        """
        self._generic_log(
            objects,
            sep, end,
            file, flush,
            tag=self.config.tag_critical,
            color_key="critical"
        )
    
    def _generic_log(
        self,
        objects: tuple,
        sep: str,
        end: str,
        file: Optional[TextIO],
        flush: bool,
        tag: str,
        color_key: str
    ) -> None:
        """
        Internal dispatcher that formats the message and routes it to console and/or file.
        
        This method handles thread locking to ensure atomic writes. It applies ANSI color
        codes if writing to the console and strips them when delegating to the file writer.
        
        Args:
            objects (tuple): The content objects to log.
            sep (str): Separator string.
            end (str): Terminator string.
            file (Optional[TextIO]): Explicit output stream override.
            flush (bool): Whether to flush the stream.
            tag (str): The string tag (e.g., [INFO]) to prepend in the log file.
            color_key (str): The key to look up in the config.colors dictionary.
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
                        
                        if message.startswith('\r'):
                            clean_msg = message[1:]
                            out_msg = f"\r{color_code}{clean_msg}{reset_code}"
                        else:
                            out_msg = f"{color_code}{message}{reset_code}"
                    
                    target_stream.write(out_msg)
                    if flush:
                        target_stream.flush()
                except Exception:
                    pass
            
            if self.config.log_to_file and file is None:
                self._write_to_file(message, tag=tag)
    
    def _write_to_file(self, text: str, tag: str) -> None:
        """
        Writes raw text to the active log file with timestamp injection.
        
        This method handles complex formatting requirements including:
        1. Checking for log rotation needs.
        2. Handling carriage returns ('\r') by seeking back to the previous entry start to overwrite it.
        3. Injecting timestamps and tags at the start of every new line.
        
        Args:
            text (str): The raw text message to write.
            tag (str): The log level tag to prepend.
        """
        if not text:
            return
        
        self._rotate_log()
        
        if self._log_file and not self._log_file.closed:
            if text.startswith('\r') and self._log_file.seekable():
                try:
                    self._log_file.seek(self._last_entry_pos)
                    self._log_file.truncate()
                    text = text.lstrip('\r')
                    self._fresh_line = True
                except OSError:
                    pass
            
            def get_preamble() -> str:
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
                    try:
                        self._last_entry_pos = self._log_file.tell()
                    except OSError:
                        pass
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
    
    def _rotate_log(self, force: bool = False) -> None:
        """
        Checks if the date has changed and rotates the log file if necessary.
        
        If the current date differs from the date associated with the open file,
        closes the current file and opens a new one named with the new date.
        
        Args:
            force (bool): If True, forces a file open operation regardless of the date check.
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
                self._last_entry_pos = self._log_file.tell()
            except OSError:
                self._log_file = None
    
    def shutdown(self) -> None:
        """
        Performs final cleanup of resources.
        
        Closes the active log file and restores standard error if it was intercepted.
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
        A helper class to intercept writes to sys.stderr and redirect them to the logger.
        """
        def __init__(self, logger_instance: 'Print'):
            self.logger = logger_instance
            self.original_stderr = logger_instance._stderr
            self.buffer = ""
        
        def write(self, message: str) -> None:
            """
            Writes a message to the original stderr and buffers it for the logger.
            Triggers a file write only when a newline is detected to ensure atomic log entries.
            """
            self.original_stderr.write(message)
            self.buffer += message
            while '\n' in self.buffer:
                line, self.buffer = self.buffer.split('\n', 1)
                full_line = line + "\n"
                with self.logger._lock:
                    if self.logger.config.log_to_file:
                        self.logger._write_to_file(full_line, tag=self.logger.config.tag_error)
        
        def flush(self) -> None:
            """
            Flushes the original stderr and forces any remaining buffer to the log file.
            """
            self.original_stderr.flush()
            if self.buffer:
                with self.logger._lock:
                    if self.logger.config.log_to_file:
                        self.logger._write_to_file(self.buffer, tag=self.logger.config.tag_error)
                self.buffer = ""
