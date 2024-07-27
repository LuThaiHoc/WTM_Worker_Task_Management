import psutil
import subprocess
from PyQt5.QtCore import QObject, pyqtSignal, QTimer
import os

class ProcessMonitor(QObject):
    signal_running_time_update = pyqtSignal(float)  # in seconds
    signal_process_started = pyqtSignal(int)
    signal_process_ended = pyqtSignal(int)
    signal_process_killed = pyqtSignal()
    signal_process_cpu_usage_update = pyqtSignal(float)  # in %
    signal_process_ram_usage_update = pyqtSignal(float)  # in MB
    signal_process_not_responding = pyqtSignal()
    
    def __init__(self, command):
        super().__init__()
        self.command = command
        self.process = None
        self.pid = None
        
        self.update_process_info_interval = 500
        self.update_process_info_timer = QTimer(self)
        self.update_process_info_timer.timeout.connect(self.update_process_info)
        
        self.update_running_time_interval = 500 # in ms
        self.update_running_time_timer = QTimer(self)
        self.update_running_time_timer.timeout.connect(self.update_time_excute)
        
        self.check_unresponsive_interval = 2000  # in ms
        self.unresponsive_timer = QTimer(self)
        self.unresponsive_timer.timeout.connect(self.check_unresponsive)
        
        self.no_process_counter = 0
        self.running_time = 0
        
        self.previous_cpu_usage = []
        self.previous_mem_usage = []
        
    def update_time_excute(self):
        self.running_time += self.update_running_time_interval/1000
        self.signal_running_time_update.emit(self.running_time)
        
    def start_process(self, log_file_path = "process_log.log"):
        print("Starting process with command: ", self.command)
        
        # self.process = subprocess.Popen(self.command, shell=True)
        # self.pid = self.process.pid
        # self.signal_process_started.emit(self.pid)
        # print(f"Process started with PID: {self.pid}")
        
        # make dir if not exist
        log_dir = os.path.dirname(log_file_path)
        if log_dir != "":
            os.makedirs(log_dir, exist_ok=True)
        
        with open(log_file_path, 'w') as log_file:
            self.process = subprocess.Popen(
                self.command,
                shell=True,
                stdout=log_file,
                stderr=log_file
            )
            self.pid = self.process.pid
            self.signal_process_started.emit(self.pid)
            print(f"Process started with PID: {self.pid}")
        
        # Start the timer to monitor the process
        self.update_process_info_timer.start(self.update_process_info_interval)  # Update process info every 1000 ms (1 second)
        self.update_running_time_timer.start(self.update_running_time_interval)
        self.unresponsive_timer.start(self.check_unresponsive_interval)
        self.running_time = 0
        
    def set_process_id(self, pid):
        self.pid = pid
    
    def get_process_info(self):
        if self.pid is None:
            print("No process started")
            return None
        
        try:
            proc = psutil.Process(self.pid)
            # Check if the process is a zombie
            if proc.status() == psutil.STATUS_ZOMBIE:
                print(f"Process {self.pid} is a defunct (zombie) process.")
                return None
            
            # Get the total CPU and memory usage of the main process and its children
            total_cpu_usage = proc.cpu_percent(interval=0.1)
            total_memory_usage = proc.memory_info().rss

            for child in proc.children(recursive=True):
                total_cpu_usage += child.cpu_percent(interval=0.1)
                total_memory_usage += child.memory_info().rss

            total_cpu_usage /= psutil.cpu_count()  # Adjust for the number of CPU cores
            total_memory_usage /= (1024 * 1024)  # Convert bytes to MB

            return {
                'pid': self.pid,
                'total_cpu_usage': total_cpu_usage,
                'total_memory_usage': total_memory_usage
            }
        except psutil.NoSuchProcess:
            self.no_process_counter += 1
            if self.no_process_counter > 5:
                print("Process not found")
                return None
            else:
                return self.no_process_counter

    def update_process_info(self):
        info = self.get_process_info()
        if isinstance(info, int):
            # print(f"Lost monitoring, Trying to find process by ID, tried: {info}")
            return
        
        if info is not None:
            # print(f"PID: {info['pid']} - Total CPU Usage: {info['total_cpu_usage']}% - Total Memory Usage: {info['total_memory_usage']} MB")
            self.signal_process_cpu_usage_update.emit(info['total_cpu_usage'])
            self.signal_process_ram_usage_update.emit(info['total_memory_usage'])
            self.no_process_counter = 0
            
            self.previous_cpu_usage.append(info['total_cpu_usage'])
            self.previous_mem_usage.append(info['total_memory_usage'])
            if len(self.previous_cpu_usage) > 60:
                self.previous_cpu_usage.pop(0)
                self.previous_mem_usage.pop(0)
        else:
            if self.process and self.process.poll() is not None:
                exit_code = self.process.returncode
                self.signal_process_ended.emit(exit_code)
            else:
                self.signal_process_ended.emit(0)
                
            self.update_process_info_timer.stop()  # Stop the timer
            self.update_running_time_timer.stop()
            self.unresponsive_timer.stop()
            # self.signal_process_ended.emit()
            self.signal_process_cpu_usage_update.emit(0)
            self.signal_process_ram_usage_update.emit(0)

    def check_unresponsive(self):
        if len(self.previous_cpu_usage) >= 60: # 10s - base on update infor timer
            # if dont use CPU or RAM in 30s, set as non responding
            if all(usage == 0 for usage in self.previous_cpu_usage) and len(set(self.previous_mem_usage)) == 1:
                print(f"Process auto emit non-responding signal - PID: {self.pid}")
                self.signal_process_not_responding.emit()
    
    def kill_process(self):
        if self.process and self.process.poll() is None:
            print("Force killing process")
            parent_proc = psutil.Process(self.pid)
            children = parent_proc.children(recursive=True)
            for child in children:
                child.terminate()
            parent_proc.terminate()
            _, alive = psutil.wait_procs(children + [parent_proc], timeout=5)
            for proc in alive:
                proc.kill()
            self.signal_process_killed.emit()
            self.update_process_info_timer.stop()
            self.update_running_time_timer.stop()
            
            self.signal_process_cpu_usage_update.emit(0)
            self.signal_process_ram_usage_update.emit(0)
            self.unresponsive_timer.stop()
            print("Process terminated")
        else:
            print("No process running to kill")
            self.signal_process_ended.emit(0) # consider that process finished
            self.update_process_info_timer.stop()
            self.update_running_time_timer.stop()
            self.unresponsive_timer.stop()

# Example usage
if __name__ == "__main__":
    command = "python /media/hoc/WORK/remote/AnhPhuong/SAT/Project/SAT_Modules/template_matching/deploy_source/main.py --avt_task_id 22 --connection_url postgresql://postgres:Pl0d9RQYUJCxZPGw6NJUcb8eJ6ZXdNMw@118.70.57.250:15445/avt"
    manager = ProcessMonitor(command)
    manager.signal_process_started.connect(lambda pid: print(f"Signal Process started with PID: {pid}"))
    manager.signal_process_ended.connect(lambda exit_code: print(f"Signal Process ended with exit code: {exit_code}"))
    manager.signal_process_cpu_usage_update.connect(lambda cpu_usage: print(f"Signal CPU Usage: {cpu_usage}%"))
    manager.signal_process_ram_usage_update.connect(lambda ram_usage: print(f"Signal RAM Usage: {ram_usage} MB"))
    manager.signal_process_killed.connect(lambda: print("Process killed"))
    
    manager.start_process()
    # manager.set_process_id(2303169)
    
    # Example of killing the process after a delay
    # QTimer.singleShot(5000, manager.kill_process)  # Kill process after 5 seconds
    
    import sys
    from PyQt5.QtWidgets import QApplication
    app = QApplication(sys.argv)
    sys.exit(app.exec_())