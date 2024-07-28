
from PyQt5.QtCore import pyqtSignal, QTimer, QObject, QCoreApplication
from typing import List
from database import *
import sys
import os
from datetime import datetime
from enum import Enum
from process_monitor import ProcessMonitor
import psutil
from exit_code import *
from system_log import logger


class StatusValue(Enum):
    WAITING = "WAITING"
    RUNNING = "RUNNING"
    FINISHED = "FINISHED"
    KILLED = "KILLED"
    NON_RESPONDING = "NON-RESPONDING"
    ERROR = "ERROR"
    UNKNOWN = "UNKNOWN"

PROCESS_LOG_DIR = '.process_log'

def format_timestamp(time : datetime):
    if time is None:
        return ""
    try:
        formatted_time = time.strftime('%H:%M:%S %d-%m-%Y')
        return formatted_time
    except ValueError:
        return "Invalid Timestamp"  # Placeholder string when ValueError occurs


class TaskItem(QObject):
    signal_status_changed = pyqtSignal()
    
    def __init__(self, task_id: int, db_connection: Database):
        super().__init__()
        self.task_id = task_id
        self.db = db_connection

        self.task = self.db.get_task_by_id(self.task_id)
        self.process_log_file_path = os.path.join(PROCESS_LOG_DIR, f"{self.task.id}.log")
        
        
        self.status = StatusValue.UNKNOWN
        self.command = ""
        self.task_cpu_usage = 0
        self.task_ram_usage = 0
        
        # Note: Really carefully consider to use auto update data from database
        # Maybe need an auto update because some time module can change task data in database (or user changes)
        # It make program take more resource and more request to the database but we can make sure the data always updated
        # Solution: Only update task data when process is running
        self.non_update_task_stat_counter = 0
        self.auto_update_task_data_interval = 1000 # auto update task form db every 3s
        self.auto_update_task_data_timer = QTimer(self)
        self.auto_update_task_data_timer.timeout.connect(self.update_task_data_from_db)
        self.auto_update_task_data_timer.start(self.auto_update_task_data_interval) # auto update data every 3s

    
    def increase_waiting_queue_position(self):
        self.update_task_data_from_db()
        if self.task.task_stat <= -2:
            self.db.update_task(self.task.id, task_stat=self.task.task_stat + 1)
            self.task.task_stat += 1
    
    def update_task_data_from_db(self):
        old_task_stat = self.task.task_stat
        self.task = self.db.get_task_by_id(self.task.id)
        self.status = self.get_status_by_stat(self.task.task_stat) # it will ignore killed status
        
        # if task started but dont update task stat (running time) for 20, consider as non-responding
        if self.task.task_stat == old_task_stat and old_task_stat > 1:
            self.non_update_task_stat_counter += 1
            # print(f"Non responding counter: {self.non_update_task_stat_counter} - PID: {self.process_monitor.pid} - TaskID: {self.task.id}")
            if self.non_update_task_stat_counter*(self.auto_update_task_data_interval/1000) > 20:
                self.process_monitor.signal_process_not_responding.emit()
        else:
            self.non_update_task_stat_counter = 0
            
        # print("Updated task: ", self.task)
        
    def update_task_command(self, command):
        self.command = command
        self.process_monitor = ProcessMonitor(command)
        self.process_monitor.signal_process_started.connect(self.process_started)
        self.process_monitor.signal_process_ended.connect(self.process_ended)
        self.process_monitor.signal_process_killed.connect(self.process_killed)
        self.process_monitor.signal_process_cpu_usage_update.connect(self.update_cpu_usage)
        self.process_monitor.signal_process_ram_usage_update.connect(self.update_ram_usage)
        self.process_monitor.signal_process_not_responding.connect(self.process_non_responding)
    
    def update_ram_usage(self, usage):
        # formatted_usage = f"{usage:.2f} MB"
        # self.ram_usage_progess.setValue(int(usage))
        # self.ram_usage_progess.setFormat(formatted_usage)
        
        self.task_ram_usage = usage
    
    def update_cpu_usage(self, usage):
        # self.cpu_usage_progess.setValue(int(usage))   
        self.task_cpu_usage = usage
    
       
    def process_killed(self):
        # update stats to database
        if not self.db.update_task(self.task.id, task_stat=0, task_message=exit_code_messages[EXIT_PROCESS_KILLED_BY_WTM]):
            # print(f"Warning: Process killed but cannot update status to database - pid: {self.task.id}")
            logger.debug(f"Warning: Process killed but cannot update status to database - pid: {self.task.id}")
        # Special update process KILLED status (because in db we set 0 value for killed/error) 
        self.task.task_stat = 0
        self.update_task_data_from_db()
    
    def process_non_responding(self):
        # print("Kill non-responding process: ", self.task.process_id)
        logger.debug("Kill non-responding process: ", self.task.process_id)
        self.kill_process()
    
    def process_ended(self, exit_code):
        # print(f"Process of task {self.task.id} end with exit code: {exit_code}")
        logger.debug(f"Process of task {self.task.id} end with exit code: {exit_code}")
        # get task data when process ended
        current_task_data = self.db.get_task_by_id(self.task.id)
        
        # if task stat not updated by module, WTM update it and message by exit code
        # Note: Module should only update task stat for finished or error status
        if current_task_data.task_stat != 0 and current_task_data.task_stat != 1: 
            if exit_code == 0:
                if not self.db.update_task(self.task.id, task_stat=1, task_message=exit_code_messages[exit_code]):
                    # print(f"Warning: Process ended but cannot update status to database - TaskID: {self.task.id}")
                    logger.debug(f"Warning: Process ended but cannot update status to database - TaskID: {self.task.id}")
                
            else: # exit code != 0 mean process not finished
                if not self.db.update_task(self.task.id, task_stat=0, task_message=exit_code_messages.get(exit_code, f"Unknown error with code {exit_code}")):
                    # print(f"Warning: Process ended but cannot update status to database - TaskID: {self.task.id}")
                    logger.debug(f"Warning: Process ended but cannot update status to database - TaskID: {self.task.id}")
                
        # update all task data when process ended (stat, output, message,...)
        self.update_task_data_from_db()

    
    def process_started(self, pid):
        self.task.process_id = pid
        # set stats to database
        if not self.db.update_task(self.task.id, process_id=pid):
            # print(f"Warning: Process started but cannot update status to database - pid: {self.task.id}")
            logger.debug(f"Warning: Process started but cannot update status to database - pid: {self.task.id}")
        
    def get_status_by_stat(self, stat) -> StatusValue:
        if stat < 0:
            return StatusValue.WAITING
        elif stat == 0:
            return StatusValue.ERROR # also killed status
        elif stat == 1:
            return StatusValue.FINISHED
        elif stat > 1:
            return StatusValue.RUNNING
        else:
            return StatusValue.UNKNOWN # never happend :)))
        
    def kill_process(self):
        # kill process...
        self.process_monitor.kill_process()
    
    def start_process(self):
        # start process
        # Let module do it
        # dont update here, not sure that module start task with input ID from task_manager
        # self.db.update_task(self.task.id, task_stat=1.5)
        self.task.task_stat = 2
        self.process_monitor.start_process(self.process_log_file_path)
        
        # Temporary update task stat to RUNNING

def getsystemStatpercent():
    # gives a single float value
    cpu_percent = psutil.cpu_percent()
    ram_percent = psutil.virtual_memory().percent
    
    return cpu_percent, ram_percent
        
class TaskManager(QObject):
    def __init__(self, config_file="config.json"):
        super().__init__()
        self.config_file = config_file
        self.task_limit = 100
        db_config = DatabaseConfig().read_from_json(self.config_file)
        self.db = Database(db_config.host, db_config.port, db_config.user, db_config.password, db_config.database)
        
        if not self.db.connected:
            # print( "Lỗi", "Không thể kết nối đến cơ sở dữ liệu, vui lòng kiểm tra lại file cấu hình!")
            logger.error( "Lỗi: Không thể kết nối đến cơ sở dữ liệu, vui lòng kiểm tra lại file cấu hình!")
            sys.exit(EXIT_CANNOT_CONNECT_TO_DATABASE)
            
        self.command_dict = self.read_module_command_dict(self.config_file, "modules")
        if self.command_dict is None:
            # print( "Error read module command", f"No section \"modules\" in {self.config_file} file, need to define it to call module for task processing")
            logger.error( "Error read module command", f"No section \"modules\" in {self.config_file} file, need to define it to call module for task processing")
            sys.exit(1)
            
        self.current_system_cpu_percent = 0
        self.current_system_ram_percent = 0
        # self.system_monitor = SystemMonitor()
        # self.system_monitor.signal_cpu_percent_updated.connect(self.update_current_system_cpu)
        # self.system_monitor.signal_ram_percent_updated.connect(self.update_current_system_ram)

        self.list_task = self.db.get_tasks(limit=self.task_limit)
        self.list_task_item = []
        
        for task in self.list_task:
            task_item = TaskItem(task.id, self.db)
            self.add_task_item(task_item)
            
        # realtime update task in database
        self.update_task_from_db_timer = QTimer(self)
        self.update_task_from_db_timer.timeout.connect(self.update_list_task_from_db)
        self.update_task_from_db_timer.start(1000)
        
        # # Currently start task by manual
        # # auto start process by process queue
        self.auto_serve_waiting_tasks_timer = QTimer(self)
        self.auto_serve_waiting_tasks_timer.timeout.connect(self.serve_waiting_tasks)  
        # self.auto_serve_waiting_tasks_timer.start(2000)
        
        self.num_waiting_value = 0
        self.num_running_value = 0
        self.num_finished_value = 0
        self.num_error_value = 0
    
    def serve_waiting_tasks(self):
        need_to_update_queue = True
        
        for task_item in self.list_task_item:
            if task_item.task.task_stat == -1: # serve task that in first queue
                
                # if have task with stat = -1 dont update queue if this task not served
                need_to_update_queue = False
                
                serve_this_task = True
                # TODO: Check current resource and decide to serve this task
                # We need to consider usage resoure by task type, difference of each task
                # It's to hard and need mode research for good policy of serve task
                # ex: simple check if current CPU and RAM usage is less then 80%
                self.current_system_cpu_percent, self.current_system_ram_percent = getsystemStatpercent()
                # print(f"CPU and RAM usage: {self.current_system_cpu_percent} - {self.current_system_ram_percent}")
                if self.current_system_cpu_percent > 60 or self.current_system_ram_percent > 60:
                    # print("=========== IGNORE SERVER TASK BECAUSE OF LESS RESOURCE ===========")
                    logger.debug(f" IGNORE SERVER TASK BECAUSE OF LESS RESOURCE - TASK ID: {task_item.task.id}")
                    serve_this_task = False
                
                # If serve a task, need to update queue
                if serve_this_task:
                    # print(f"Serve task with id: {task_item.task.id} - Name: {task_item.task.creator}")
                    logger.debug(f"Serve task with id: {task_item.task.id} - Name: {task_item.task.creator}")
                    task_item.start_process()
                    need_to_update_queue = True
                    # only serve one task when call serve_waiting_tasks function 
                    # it prevent serve case that server multi task at the same time, can cause machine overload
                    break  
        
        # if this task was served, increase others queue
        if need_to_update_queue:
            for task_item in self.list_task_item:
                task_item.increase_waiting_queue_position()
                if (task_item.task.task_stat <= -1):
                    # print(f"Task id: {task_item.task.id}, Queue value: {task_item.task.task_stat}, Task type: {task_item.task.task_type}")
                    logger.debug(f"Task id: {task_item.task.id}, Queue value: {task_item.task.task_stat}, Task type: {task_item.task.task_type}") 
        
        self.update_task_statictics()
        
    def update_current_system_ram(self, value):
        self.current_system_ram_percent = value
    
    def update_current_system_cpu(self, value):
        self.current_system_cpu_percent = value
    
    def add_task_item(self, task_widget: TaskItem, index=-1): # default to end of list
        command = self.command_dict.get(str(int(task_widget.task.task_type)), "")
        full_command = f"{command} --avt_task_id {task_widget.task.id} --config_file {self.config_file}" 
        # print("Set task command: ", full_command)
        task_widget.update_task_command(full_command)
        self.list_task_item.insert(index, task_widget)        
        
    def update_list_task_from_db(self):
        new_task_list = self.db.get_tasks(limit=self.task_limit)
        
        # Create sets for comparison
        current_task_ids = {task.id for task in self.list_task}
        new_task_ids = {task.id for task in new_task_list}
        
        # Tasks to add
        tasks_to_add = [task for task in new_task_list if task.id not in current_task_ids]
        
        # Tasks to remove
        tasks_to_remove = [task for task in self.list_task if task.id not in new_task_ids]
        
        # Remove tasks
        for task in tasks_to_remove:
            index = self.list_task.index(task)
            # print("Remove old task with id: ", task.id)
            logger.debug("Remove old task with id: ", task.id)
            self.list_task.remove(task)
            self.list_task_item.pop(index)
            
        # Add new tasks to the beginning of the table and lists
        for task in reversed(tasks_to_add):  # Reverse to add to the top
            self.list_task.insert(0, task)
            task_widget = TaskItem(task.id, self.db)  # Assuming TaskItem is correctly defined
            # self.list_task_item.insert(0, task_widget)
            self.add_task_item(task_widget, 0)
            # print("Add new task with id: ", task.id)
            logger.debug("Add new task with id: ", task.id)
        
    
    def read_module_command_dict(self, config_file, section):
        try:
            # Read the JSON file
            with open(config_file, 'r') as file:
                data = json.load(file)
            
            # Extract the section
            section = data.get(section, None)
            
            if section is None:
                raise KeyError(f"Section '{section}' not found in the JSON file.")
            
            return section
        
        except FileNotFoundError:
            # print(f"Error: The file {config_file} does not exist.")
            logger.error(f"Error: The file {config_file} does not exist.")
            return None
        except json.JSONDecodeError:
            # print("Error: The file is not a valid JSON.")
            logger.error("Error: The file is not a valid JSON.")
            return None
        except Exception as e:
            # print(f"An error occurred: {e}")
            logger.error(f"An error occurred: {e}")
            return None

        
    def update_task_statictics(self):
        self.num_waiting_value = sum(1 for task_item in self.list_task_item if (task_item.status == StatusValue.WAITING))
        self.num_running_value = sum(1 for task_item in self.list_task_item if (task_item.status == StatusValue.RUNNING))
        self.num_finished_value = sum(1 for task_item in self.list_task_item if (task_item.status == StatusValue.FINISHED))
        self.num_error_value = sum(1 for task_item in self.list_task_item if (task_item.status == StatusValue.KILLED or task_item.status == StatusValue.ERROR))
        logger.debug(f"Waiting: {self.num_waiting_value}\tRunning: {self.num_running_value}\tFinish: {self.num_finished_value}\tkilled/error: {self.num_error_value}")

import signal
def signal_handler(sig, frame):
    print("Interrupt received, stopping...")
    logger.debug("Interrupt received, stopping...")
    app.quit()  # Stop the event loop and exit the application

if __name__ == "__main__":
    app = QCoreApplication(sys.argv)  # Initialize Qt application for non-UI

    # Set up signal handler for keyboard interrupt (Ctrl+C)
    signal.signal(signal.SIGINT, signal_handler)

    task_manager = TaskManager()
    task_manager.auto_serve_waiting_tasks_timer.start(5000)
    
    try:
        app.exec_()  # Start the event loop
    except KeyboardInterrupt:
        print("Stop program")
        sys.exit(0)  # Exit the program cleanly
    