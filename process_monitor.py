import psutil
import subprocess
from PyQt5.QtCore import QObject, pyqtSignal, QTimer

class ProcessMonitor(QObject):
    signal_running_time_update = pyqtSignal(float)  # in seconds
    signal_process_started = pyqtSignal()
    signal_process_ended = pyqtSignal()
    signal_process_killed = pyqtSignal()
    signal_process_cpu_usage_update = pyqtSignal(float)  # in %
    signal_process_ram_usage_update = pyqtSignal(float)  # in MB
    
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
        
        self.no_process_counter = 0
        self.running_time = 0
        
    def update_time_excute(self):
        self.running_time += self.update_running_time_interval/1000
        self.signal_running_time_update.emit(self.running_time)
        
    def start_process(self):
        self.process = subprocess.Popen(self.command, shell=True)
        self.pid = self.process.pid
        self.signal_process_started.emit()
        print(f"Process started with PID: {self.pid}")
        
        # Start the timer to monitor the process
        self.update_process_info_timer.start(self.update_process_info_interval)  # Update process info every 1000 ms (1 second)
        self.update_running_time_timer.start(self.update_running_time_interval)
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
            print(f"Lost monitoring, Trying to find process by ID, tried: {info}")
            return
        
        if info is not None:
            # print(f"PID: {info['pid']} - Total CPU Usage: {info['total_cpu_usage']}% - Total Memory Usage: {info['total_memory_usage']} MB")
            self.signal_process_cpu_usage_update.emit(info['total_cpu_usage'])
            self.signal_process_ram_usage_update.emit(info['total_memory_usage'])
            self.no_process_counter = 0
        else:
            self.update_process_info_timer.stop()  # Stop the timer
            self.update_running_time_timer.stop()
            self.signal_process_ended.emit()
            self.signal_process_cpu_usage_update.emit(0)
            self.signal_process_ram_usage_update.emit(0)
            print("Process ended")

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
            # self.unresponsive_timer.stop()
            print("Process terminated")
        else:
            print("No process running to kill")
            self.signal_process_ended.emit()
            self.update_process_info_timer.stop()
            self.update_running_time_timer.stop()
            # self.unresponsive_timer.stop()

# Example usage
if __name__ == "__main__":
    command = "python /media/hoc/WORK/remote/AnhPhuong/SAT/Project/SAT_Modules/template_matching/main.py"
    manager = ProcessMonitor(command)
    manager.signal_process_started.connect(lambda: print("Signal Process started"))
    manager.signal_process_ended.connect(lambda: print("Signal Process ended"))
    manager.signal_process_cpu_usage_update.connect(lambda cpu_usage: print(f"Signal CPU Usage: {cpu_usage}%"))
    manager.signal_process_ram_usage_update.connect(lambda ram_usage: print(f"Signal RAM Usage: {ram_usage} MB"))
    manager.signal_process_killed.connect(lambda: print("Process killed"))
    
    manager.start_process()
    # manager.set_process_id(2303169)
    
    # Example of killing the process after a delay
    QTimer.singleShot(5000, manager.kill_process)  # Kill process after 5 seconds
    
    import sys
    from PyQt5.QtWidgets import QApplication
    app = QApplication(sys.argv)
    sys.exit(app.exec_())