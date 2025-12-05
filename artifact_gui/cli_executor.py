"""
CLI Executor - Handles execution of rdfm-artifact commands
"""

import queue
import subprocess
import threading
from collections.abc import Callable
from functools import partial

from artifact_gui.logger import get_logger
from artifact_gui.ui_constants import COMMAND_DISPLAY_MAX_LENGTH
from artifact_gui.utils import truncate_text

logger = get_logger(__name__)


class CLIExecutor:
    """Executes rdfm-artifact CLI commands in separate threads"""

    def __init__(self, output_queue: "queue.Queue[tuple]") -> None:
        """Initialize the CLI executor

        Args:
            output_queue: Queue for thread-safe output messages
        """
        self.output_queue = output_queue

        # Track running process for cancellation
        self.current_process: subprocess.Popen | None = None
        self.process_lock = threading.Lock()
        self.is_running = False
        self.cancel_requested = False

    def cancel_command(self, force: bool = False) -> bool:
        """Cancel the currently running command

        Args:
            force: If True, forcibly kill the process.
                   If False, try graceful termination.

        Returns:
            True if cancellation was successful, False otherwise
        """
        with self.process_lock:
            if self.current_process and self.is_running:
                try:
                    if force or self.cancel_requested:
                        # Force kill
                        self.current_process.kill()
                        self.output_queue.put(
                            ("output", "\n\n--- Command forcibly killed ---\n")
                        )
                        self.output_queue.put(("status", "Command killed"))
                        self.output_queue.put(("command_finished", None))
                        self.cancel_requested = False
                    else:
                        # Graceful termination
                        self.cancel_requested = True
                        self.current_process.terminate()
                        self.output_queue.put(
                            (
                                "output",
                                (
                                    "\n\n--- Cancellation requested, "
                                    "waiting for graceful shutdown... ---\n"
                                ),
                            )
                        )
                        self.output_queue.put(("status", "Trying to cancel..."))
                        self.output_queue.put(("cancel_requested", None))
                    return True
                except Exception as e:
                    self.output_queue.put(
                        ("output", f"\nError cancelling command: {e!s}\n")
                    )
                    return False
        return False

    def reset_cancel_state(self) -> None:
        """Reset the cancel state after command finishes"""
        with self.process_lock:
            self.cancel_requested = False

    def is_command_running(self) -> bool:
        """Check if a command is currently running

        Returns:
            True if a command is running, False otherwise
        """
        with self.process_lock:
            return self.is_running

    def set_current_process(
        self, process: subprocess.Popen | None, is_running: bool = True
    ) -> None:
        """Set the current process and running state (thread-safe)

        Args:
            process: The subprocess.Popen object to track
            is_running: Whether to mark the command as running
        """
        with self.process_lock:
            self.current_process = process
            self.is_running = is_running

    def clear_current_process(self) -> None:
        """Clear the current process and mark as not running (thread-safe)"""
        with self.process_lock:
            self.current_process = None
            self.is_running = False

    # Read stdout in real-time
    def _read_stdout(self, process: subprocess.Popen, output: list) -> None:
        try:
            for line in iter(process.stdout.readline, ""):
                if line:
                    output.append(line)
                    self.output_queue.put(("output", line))
        except Exception:
            pass
        finally:
            process.stdout.close()

    # Read stderr in real-time (rdfm-artifact uses stderr for progress)
    def _read_stderr(self, process: subprocess.Popen, output: list) -> None:
        try:
            for line in iter(process.stderr.readline, ""):
                if line:
                    output.append(line)
                    self.output_queue.put(("output", line))
        except Exception:
            pass
        finally:
            process.stderr.close()

    def _run_process(self, process: subprocess.Popen) -> tuple[str, int]:
        stdout_output = []
        stderr_output = []

        # Read stdout in real-time
        read_stdout = partial(self._read_stdout, process, stdout_output)

        read_stderr = partial(self._read_stderr, process, stderr_output)

        # Start threads to read stdout and stderr
        stdout_thread = threading.Thread(target=read_stdout, daemon=True)
        stderr_thread = threading.Thread(target=read_stderr, daemon=True)
        stdout_thread.start()
        stderr_thread.start()

        # Wait for process to complete
        process.wait()
        stdout_thread.join()
        stderr_thread.join()
        return "".join(stdout_output), process.returncode

    def run_artifact_command(
        self,
        *args: str,
        callback: Callable[[str], None] | None = None,
        success_message: str | None = None,
    ) -> None:
        """Run an rdfm-artifact command in a separate thread

        Args:
            *args: Command arguments (e.g., 'read', 'file.rdfm')
            callback: Function to call on success with stdout as argument
            success_message: Message to display in output when command
                succeeds but produces no output
        """

        def execute() -> None:
            try:
                # Build command
                cmd = ["rdfm-artifact", *list(args)]
                logger.info(f"Executing command: {' '.join(cmd)}")

                # Display command being run
                display_cmd = truncate_text(" ".join(cmd), COMMAND_DISPLAY_MAX_LENGTH)
                self.output_queue.put(("status", f"Running: {display_cmd}"))
                self.output_queue.put(("clear", None))
                self.output_queue.put(("command_started", None))

                # Run the command with streaming output using Popen
                with self.process_lock:
                    self.current_process = subprocess.Popen(
                        cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        bufsize=1,
                    )
                    self.is_running = True

                process = self.current_process

                full_stdout, returncode = self._run_process(process)

                # Mark as no longer running
                with self.process_lock:
                    self.is_running = False
                    self.current_process = None

                if returncode == 0:
                    logger.info("Command completed successfully")
                    self.output_queue.put(("status", "Command completed successfully"))
                    if not full_stdout and success_message:
                        self.output_queue.put(("output", success_message))
                    if callback:
                        callback(full_stdout)
                else:
                    logger.error(f"Command failed with return code {returncode}")
                    self.output_queue.put(
                        ("status", f"Command failed with code {returncode}")
                    )

                self.output_queue.put(("command_finished", None))

            except FileNotFoundError:
                with self.process_lock:
                    self.is_running = False
                    self.current_process = None
                self.output_queue.put(
                    (
                        "output",
                        "Error: Command 'rdfm-artifact' not found.\n"
                        "Please ensure rdfm-artifact is installed and in your PATH.",
                    )
                )
                self.output_queue.put(("status", "Command not found"))
                self.output_queue.put(("command_finished", None))
            except Exception as e:
                with self.process_lock:
                    self.is_running = False
                    self.current_process = None
                self.output_queue.put(("output", f"Exception: {e!s}"))
                self.output_queue.put(("status", "Command failed"))
                self.output_queue.put(("command_finished", None))

        # Start command in new thread
        thread = threading.Thread(target=execute, daemon=True)
        thread.start()
