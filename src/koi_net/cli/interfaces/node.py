import os
import shutil
import subprocess
import sys
import threading
import time

from ..consts import CONFIG, GET, INIT, READY_SIGNAL, RUN, SET, STOP_SIGNAL, UNSET, WIPE
from ..exceptions import MissingEnvVariablesError, LocalNodeExistsError


"""
entry point name -> module name -> node class, run node

node name (directory)
node type alias (entrypoint: `coordinator`)
node type name (module: `koi_net_coordinator_node`)

node name -> node type name: (stored in koi net config)
"""


class NodeInterface:
    def __init__(self, name: str, module: str):
        self.name = name
        self.module = module
        self.process = None
        self.process_ready = threading.Event()
        
    def execute(self, *args, pipe: bool = False):
        return subprocess.Popen(
            args=(sys.executable, "-m", self.module, *args),
            cwd=self.name,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
            stdin=subprocess.PIPE if pipe else None,
            stdout=subprocess.PIPE if pipe else None,
            stderr=subprocess.PIPE if pipe else None,
            text=True,
            bufsize=1)
    
    def create(self):
        print(f"Creating {self.name}...")
        try:
            os.mkdir(self.name)
        except FileExistsError:
            raise LocalNodeExistsError(f"Node of name '{self.name}' already exists")
    
    def exists(self) -> bool:
        return os.path.isdir(self.name)
    
    def init(self):
        self.execute(INIT).wait()
    
    def wipe(self):
        self.execute(WIPE).wait()
        
    def get_config(self, jp: str):
        process = self.execute(CONFIG, GET, jp, pipe=True)
        return process.stdout.read().rstrip("\n")
    
    def set_config(self, jp: str, val: str):
        self.execute(CONFIG, SET, jp, val).wait()
        
    def unset_config(self, jp: str):
        self.execute(CONFIG, UNSET, jp).wait()
    
    def delete(self):
        shutil.rmtree(self.name)
    
    def watch_stdout(self, mirror: bool = False):
        for line in self.process.stdout:
            if mirror:
                sys.stdout.write(line)
                sys.stdout.flush()
            if line.strip() == READY_SIGNAL:
                self.process_ready.set()
            elif READY_SIGNAL in line:
                sys.stdout.write(f"found signal in stdout!\n{line}\n")
                sys.stdout.flush()
    
    def watch_stderr(self):
        for line in self.process.stderr:
            sys.stderr.write(line)
            sys.stderr.flush()
    
    def start(self, verbose: bool = False) -> bool:
        print(f"Starting {self.name}...", end=" ", flush=True)
        self.process = self.execute(RUN, pipe=True)
        threading.Thread(target=self.watch_stdout, args=(verbose,), daemon=True).start()
        threading.Thread(target=self.watch_stderr, daemon=True).start()
            
        success = self.process_ready.wait(timeout=5)
        if success:
            print("Done")
        else:
            print("Timed out")
        
        return success
        
    def stop(self) -> bool:
        print(f"Stopping {self.name}...", end=" ", flush=True)
        if not self.process:
            return False
        
        self.process.stdin.write(STOP_SIGNAL + "\n")
        self.process.stdin.flush()
        self.process.stdin.close()
        
        try:
            self.process.wait(timeout=5)
            print("Done")
            return True
        
        except subprocess.TimeoutExpired:
            print("Timed out")
            return False
        
    def run(self, verbose: bool = False):
        self.start(verbose=verbose)
        print("Press Ctrl + C to quit")
        try:
            while self.process.poll() is None:
                time.sleep(0.5)
        except KeyboardInterrupt:
            pass
        finally:
            self.stop()
