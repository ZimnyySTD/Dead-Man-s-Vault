"""Lightweight, non-blocking process launcher and running-state monitor for Dead Man's Vault."""

import logging
import os
import shlex
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, List, Optional

from DeadMansVault.Library.GameDefinitions.game_model import GameEntry
from DeadMansVault.Library.GameRegistry.game_registry import GameRegistry

logger = logging.getLogger("DeadMansVault.GameRunner")


@dataclass
class RunningGameProcess:
    game_id: str
    process: subprocess.Popen
    started_at: float
    command: List[str]


class GameRunner:
    def __init__(self, registry: GameRegistry):
        self.registry = registry
        self.running_processes: Dict[str, RunningGameProcess] = {}
        self.lock = threading.RLock()
        self._state_change_callbacks: List[Callable[[str, bool], None]] = []

    def register_state_change_callback(self, cb: Callable[[str, bool], None]) -> None:
        self._state_change_callbacks.append(cb)

    def _notify_state_change(self, game_id: str, is_running: bool) -> None:
        for cb in self._state_change_callbacks:
            try:
                cb(game_id, is_running)
            except Exception as e:
                logger.error(f"Error in runner state change callback: {e}")

    def is_game_running(self, game_id: str) -> bool:
        with self.lock:
            if game_id not in self.running_processes:
                return False
            proc = self.running_processes[game_id].process
            poll_result = proc.poll()
            if poll_result is None:
                return True
            del self.running_processes[game_id]
            return False

    def launch_game(
        self,
        game_id: str,
        custom_args: Optional[str] = None,
        working_dir: Optional[Path] = None,
    ) -> subprocess.Popen:
        with self.lock:
            if self.is_game_running(game_id):
                raise RuntimeError(f"Game '{game_id}' is already running.")

            entry = self.registry.get_game(game_id)
            if not entry or not entry.is_installed or not entry.installation:
                raise FileNotFoundError(f"Game '{game_id}' is not installed.")

            exec_path = Path(entry.installation.executable_path).resolve()
            if not exec_path.exists():
                raise FileNotFoundError(f"Game executable not found: {exec_path}")

            if sys.platform != "win32" and not os.access(exec_path, os.X_OK):
                try:
                    exec_path.chmod(exec_path.stat().st_mode | 0o111)
                except Exception:
                    pass

            cwd = (
                Path(working_dir).resolve()
                if working_dir
                else Path(entry.installation.working_directory or exec_path.parent).resolve()
            )

            cmd = [str(exec_path)]
            args_str = custom_args if custom_args is not None else entry.installation.custom_arguments
            if not args_str and entry.definition.launch_arguments:
                args_str = entry.definition.launch_arguments

            if args_str:
                cmd.extend(shlex.split(args_str))

            logger.info(f"Launching game '{game_id}': {' '.join(cmd)} (cwd={cwd})")

            entry.installation.last_played = time.time()
            self.registry.save_installations()

            proc = subprocess.Popen(
                cmd,
                cwd=str(cwd),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

            running = RunningGameProcess(
                game_id=game_id,
                process=proc,
                started_at=time.time(),
                command=cmd,
            )
            self.running_processes[game_id] = running

        self._notify_state_change(game_id, True)

        watcher_thread = threading.Thread(
            target=self._watch_process,
            args=(game_id, proc),
            daemon=True,
        )
        watcher_thread.start()

        return proc

    def _watch_process(self, game_id: str, proc: subprocess.Popen) -> None:
        exit_code = proc.wait()
        logger.info(f"Game '{game_id}' exited with code {exit_code}")

        with self.lock:
            if game_id in self.running_processes:
                del self.running_processes[game_id]

        self._notify_state_change(game_id, False)

    def stop_game(self, game_id: str, timeout: float = 3.0) -> bool:
        with self.lock:
            if game_id not in self.running_processes:
                return False
            proc = self.running_processes[game_id].process

        try:
            import signal
            try:
                os.kill(proc.pid, signal.SIGTERM)
            except Exception:
                proc.terminate()

            try:
                proc.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                try:
                    os.kill(proc.pid, signal.SIGKILL)
                except Exception:
                    proc.kill()
                proc.wait(timeout=1.0)
            return True
        except Exception as e:
            logger.error(f"Error terminating game {game_id}: {e}")
            return False
