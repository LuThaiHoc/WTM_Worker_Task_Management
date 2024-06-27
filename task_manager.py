from PyQt5.QtWidgets import (
    QMessageBox, QFormLayout, QListWidget, QListWidgetItem, QDateTimeEdit,
    QApplication, QWidget, QDialog, QVBoxLayout, QLabel, QLineEdit, QPushButton,
    QHBoxLayout, QComboBox, QCheckBox, QFileDialog, QProgressDialog, QSizePolicy, QProgressBar, QGridLayout, QSpacerItem,
    QTableWidget, QTableWidgetItem, QHeaderView
)
from PyQt5.QtGui import QFont, QImage, QPixmap, QDesktopServices, QColor, QMouseEvent
from PyQt5.QtCore import pyqtSignal, QDateTime, Qt, QUrl, QTimer
from typing import List
from database import *
import sys
import os
from datetime import datetime
from enum import Enum
from process_monitor import ProcessMonitor
import psutil
from exit_code import *

status_colors = {
    "WAITING": QColor(255, 255, 0),    # Yellow
    "RUNNING": QColor(0, 255, 0),      # Green
    "FINISHED": QColor(0, 0, 255),     # Blue
    "KILLED": QColor(255, 0, 0),       # Red
    "ERROR": QColor(255, 165, 0),       # Orange
    "UNKNOWN": QColor(255, 255, 255)  
}

task_types = {
    1 : "Correction",
    2 : "Pre-Process",
    3 : "Cloud removed",
    4 : "Enhancement",
    5 : "Detection",
    6 : "Classification",
    7 : "Object finder",
    8 : "Others",
}

class StatusValue(Enum):
    WAITING = "WAITING"
    RUNNING = "RUNNING"
    FINISHED = "FINISHED"
    KILLED = "KILLED"
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
    
class CustomTableWidget(QTableWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        child = self.childAt(event.pos())
        if child:
            event = QMouseEvent(event.type(), child.mapFromParent(event.pos()), event.button(), event.buttons(), event.modifiers())
            QApplication.sendEvent(child, event)

class HeaderLabel(QLabel):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        header_font = QFont("Arial Unicode MS", 14, QFont.Bold)
        self.setFont(header_font)
        self.setStyleSheet("color: #f0f0f0;")  # Example color for headers, adjust as needed

class ValueLabel(QLabel):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        value_font = QFont("Arial Unicode MS", 13)
        self.setFont(value_font)
        self.setStyleSheet("color: #e0e0e0;")  # Example color for values, adjust as needed

class TaskItem(QWidget):
    signal_status_changed = pyqtSignal()
    
    def __init__(self, task_data: AvtTask):
        super().__init__()
        self.task = task_data
        db_config = DatabaseConfig().read_from_json("config.json")
        self.db = Database(db_config.host, db_config.port, db_config.user, db_config.password, db_config.database)
        self.process_log_file_path = os.path.join(PROCESS_LOG_DIR, f"{self.task.id}.log")
        
        self.main_layout = QHBoxLayout()
        self.grid_layout = QGridLayout()
        
        self.status_layout = QHBoxLayout()
        self.status_label = QLabel("")
        # self.status_label.setFixedWidth(100)
        self.status_label.setMinimumWidth(100)
        
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_layout.addWidget(self.status_label)
        
        self.create_at_header = HeaderLabel("Khởi tạo:")
        self.create_at_value = ValueLabel(format_timestamp(self.task.created_at))
        self.update_at_header = HeaderLabel("Cập nhật:")
        self.update_at_value = ValueLabel(format_timestamp(self.task.updated_at))
        self.creator_header = HeaderLabel("Người tạo:")
        self.creator_value = ValueLabel(self.task.creator)
        self.type_header = HeaderLabel("Type:")
        task_type_value = task_types.get(self.task.type, "Unknown")
        self.type_value = ValueLabel(task_type_value)
        
        
        self.cpu_usage_header = HeaderLabel("CPU usage (%)")
        self.ram_usage_header = HeaderLabel("RAM usage (MB)")
        
        self.cpu_usage_progess = QProgressBar()
        self.cpu_usage_progess.setMinimumWidth(200)
        self.cpu_usage_progess.setRange(0, 100)
        self.cpu_usage_progess.setValue(0)
        
        self.ram_usage_progess = QProgressBar()
        self.ram_usage_progess.setMinimumWidth(200)
        max_ram = int(psutil.virtual_memory().total // (1024 ** 2))  # Example maximum RAM value (16GB)
        ram_usage_mb = 0  # Example actual RAM usage (in MB)
        self.ram_usage_progess.setRange(0, max_ram)
        self.ram_usage_progess.setValue(ram_usage_mb)
        self.ram_usage_progess.setFormat(f"{ram_usage_mb} MB")
        
        self.time_excute_header = HeaderLabel("Thực thi:")
        self.time_excute_value = ValueLabel("0s")
        self.time_excute_value.setAlignment(Qt.AlignCenter)
        self.time_remain_header = HeaderLabel("ETA:")
        self.time_remain_value = ValueLabel(f"{str(self.task.task_eta)}s")
        self.time_remain_value.setAlignment(Qt.AlignCenter)
        
        # Adding widgets to the grid layout
        self.grid_layout.addWidget(self.create_at_header, 0, 0)
        self.grid_layout.addWidget(self.create_at_value, 0, 1)
        self.grid_layout.addWidget(self.update_at_header, 1, 0)
        self.grid_layout.addWidget(self.update_at_value, 1, 1)

        # Adding spacer between column pairs
        spacer = QSpacerItem(20, 20, QSizePolicy.Minimum, QSizePolicy.Minimum)
        self.grid_layout.addItem(spacer, 0, 2, 1, 1)
        self.grid_layout.addItem(spacer, 1, 2, 1, 1)

        self.grid_layout.addWidget(self.creator_header, 0, 3)
        self.grid_layout.addWidget(self.creator_value, 0, 4)
        self.grid_layout.addWidget(self.type_header, 1, 3)
        self.grid_layout.addWidget(self.type_value, 1, 4)
        
        spacer2 = QSpacerItem(20, 20, QSizePolicy.Minimum, QSizePolicy.Minimum)
        self.grid_layout.addItem(spacer2, 0, 5, 1, 1)
        self.grid_layout.addItem(spacer2, 1, 5, 1, 1)

        self.grid_layout.addWidget(self.cpu_usage_header, 0, 6)
        self.grid_layout.addWidget(self.cpu_usage_progess, 0, 7)
        self.grid_layout.addWidget(self.ram_usage_header, 1, 6)
        self.grid_layout.addWidget(self.ram_usage_progess, 1, 7)
        
        spacer3 = QSpacerItem(20, 20, QSizePolicy.Minimum, QSizePolicy.Minimum)
        self.grid_layout.addItem(spacer3, 0, 8, 1, 1)
        self.grid_layout.addItem(spacer3, 1, 8, 1, 1)

        self.grid_layout.addWidget(self.time_excute_header, 0, 9)
        self.grid_layout.addWidget(self.time_excute_value, 0, 10)
        self.grid_layout.addWidget(self.time_remain_header, 1, 9)
        self.grid_layout.addWidget(self.time_remain_value, 1, 10)
        
        spacer4 = QSpacerItem(20, 20, QSizePolicy.Minimum, QSizePolicy.Minimum)
        self.grid_layout.addItem(spacer4, 0, 11, 1, 1)
        self.grid_layout.addItem(spacer4, 1, 11, 1, 1)
        
        self.start_process_button = QPushButton("Start Process")
        self.kill_process_button = QPushButton("Kill Process")
        self.grid_layout.addWidget(self.start_process_button, 0, 12)
        self.grid_layout.addWidget(self.kill_process_button, 1, 12)

        self.main_layout.addLayout(self.status_layout)
        self.main_layout.addLayout(self.grid_layout)
        self.main_layout.setSpacing(10)
        self.setLayout(self.main_layout)
        
        self.status = StatusValue.UNKNOWN
        self.update_task_status(self.get_status_by_stat(self.task.task_stat))
        self.start_process_button.clicked.connect(self.start_process)
        self.kill_process_button.clicked.connect(self.kill_process)
        
        self.command = ""
        
        # TODO: View task details widget
    
        # Note: Really carefully consider to use auto update data from database
        # Maybe need an auto update because some time module can change task data in database (or user changes)
        # It make program take more resource and more request to the database but we can make sure the data always updated
        # Solution: Only update task data when process is running
        self.auto_update_task_data_timer = QTimer(self)
        self.auto_update_task_data_timer.timeout.connect(self.auto_update_task_data_from_db)
        self.auto_update_task_data_timer.start(3000) # auto update data every 3s
    
    def increase_waiting_queue_position(self):
        self.update_task_data_from_db()
        if self.task.task_stat <= -2:
            self.db.update_task(self.task.id, task_stat=self.task.task_stat + 1)
            self.task.task_stat += 1
    
    def auto_update_task_data_from_db(self):
        # Only auto update task data when it is running because module processing can change task data in database
        if self.status != StatusValue.RUNNING:
            return
        self.task = self.db.get_task_by_id(self.task.id)
        new_task_status = self.get_status_by_stat(self.task.task_stat) # it will ignore killed status
        
        # update status display
        if self.status != new_task_status and self.status != StatusValue.KILLED:
            self.update_task_status(new_task_status)
            
        # update data that can be changed by modules
        self.update_at_value.setText(format_timestamp(self.task.updated_at))
        self.time_remain_value.setText(f"{str(self.task.task_eta)}s")
    
    def update_task_data_from_db(self):
        self.task = self.db.get_task_by_id(self.task.id)
        new_task_status = self.get_status_by_stat(self.task.task_stat) # it will ignore killed status
        
        # update status display
        if self.status != new_task_status and self.status != StatusValue.KILLED:
            self.update_task_status(new_task_status)
            
        # update information
        self.update_at_value.setText(format_timestamp(self.task.updated_at))
        self.time_remain_value.setText(f"{str(self.task.task_eta)}s") # maybe module udpate ETA while processing
    
     
    def update_task_command(self, command):
        self.command = command
        self.process_monitor = ProcessMonitor(command)
        self.process_monitor.signal_process_started.connect(self.process_started)
        self.process_monitor.signal_process_ended.connect(self.process_ended)
        self.process_monitor.signal_process_killed.connect(self.process_killed)
        self.process_monitor.signal_running_time_update.connect(self.update_running_time)
        self.process_monitor.signal_process_cpu_usage_update.connect(self.update_cpu_usage)
        self.process_monitor.signal_process_ram_usage_update.connect(self.update_ram_usage)
        self.process_monitor.signal_process_not_responding.connect(self.process_non_responding)
    
    def update_running_time(self, value):
        self.time_excute_value.setText(f"{value}s")
        # update running time in task stat
        if value > 1: # only update running time > 1 in task_stat to avoid confilict with tast_stat=1 (finished) or task_stat = 0 (error)
            self.db.update_task(self.task.id, task_stat=value)
            self.task.task_stat = value
        
    def process_killed(self):
        # update stats to database
        if not self.db.update_task(self.task.id, task_stat=0, task_message=exit_code_messages[EXIT_PROCESS_KILLED_BY_WTM]):
            print(f"Warning: Process killed but cannot update status to database - pid: {self.task.id}")
        # Special update process KILLED status (because in db we set 0 value for killed/error) 
        self.task.task_stat = 0
        self.update_task_status(StatusValue.KILLED)
        self.update_task_data_from_db()
    
    def process_non_responding(self):
        # print(f"Process {self.command} is not responding..")
        # TODO: Hanle not-responding, ask user for kill this process or auto kill
        self.status_label.setText("NOT RESPONDING")
        self.status_label.setStyleSheet(f"font-size: 10pt; font-weight: bold; color: {status_colors[StatusValue.ERROR.value].name()};")
        print("Kill non-responding process: ", self.task.process_id)
        self.kill_process()
    
    def process_ended(self, exit_code):
        print(f"Process of task {self.task.id} end with exit code: {exit_code}")
        # get task data when process ended
        current_task_data = self.db.get_task_by_id(self.task.id)
        
        # if task stat not updated by module, WTM update it and message by exit code
        # Note: Module should only update task stat for finished or error status
        if current_task_data.task_stat != 0 and current_task_data.task_stat != 1: 
            if exit_code == 0:
                if not self.db.update_task(self.task.id, task_stat=1, task_message=exit_code_messages[exit_code]):
                    print(f"Warning: Process ended but cannot update status to database - TaskID: {self.task.id}")
                
            else: # exit code != 0 mean process not finished
                if not self.db.update_task(self.task.id, task_stat=0, task_message=exit_code_messages.get(exit_code, f"Unknown error with code {exit_code}")):
                    print(f"Warning: Process ended but cannot update status to database - TaskID: {self.task.id}")
                
        # update all task data when process ended (stat, output, message,...)
        self.update_task_data_from_db()

    
    def process_started(self, pid):
        self.task.process_id = pid
        # set stats to database
        if not self.db.update_task(self.task.id, process_id=pid):
            print(f"Warning: Process started but cannot update status to database - pid: {self.task.id}")
        # update status
        self.update_task_status(StatusValue.RUNNING)
        
    
    def update_ram_usage(self, usage):
        formatted_usage = f"{usage:.2f} MB"
        self.ram_usage_progess.setValue(int(usage))
        self.ram_usage_progess.setFormat(formatted_usage)
    
    def update_cpu_usage(self, usage):
        self.cpu_usage_progess.setValue(int(usage))   
             
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
        # temporary update process stat for get out of WAITING queue (status)
        self.db.update_task(self.task.id, task_stat=1.5)
        self.task.task_stat = 1.5
        self.process_monitor.start_process(self.process_log_file_path)

        
    def update_task_status(self, new_status : StatusValue):
        if self.status != new_status:
            self.status = new_status
            self.signal_status_changed.emit()
        
            self.status_label.setText(self.status.value)
            self.status_label.setStyleSheet(f"font-size: 12pt; font-weight: bold; color: {status_colors[self.status.value].name()};")
        
        # Update any other relevant UI elements based on the new status
        if self.status == StatusValue.RUNNING:
            self.start_process_button.setEnabled(False)
            self.kill_process_button.setEnabled(True)
        elif self.status == StatusValue.FINISHED:
            self.start_process_button.setEnabled(False)
            self.kill_process_button.setEnabled(False)
        elif self.status == StatusValue.WAITING:
            self.start_process_button.setEnabled(True)
            self.kill_process_button.setEnabled(False)
        elif self.status == StatusValue.ERROR or self.status == StatusValue.KILLED:
            self.start_process_button.setEnabled(True)
            self.kill_process_button.setEnabled(False)
            
        

from system_monitor.systemMonitor import SystemMonitor
class Ui_TaskManager(QWidget):
    def __init__(self, config_file="config.json"):
        super().__init__()
        self.config_file = config_file
        self.task_limit = 10
        db_config = DatabaseConfig().read_from_json(self.config_file)
        self.db = Database(db_config.host, db_config.port, db_config.user, db_config.password, db_config.database)

        self.main_layout = QVBoxLayout()
        self.top_layout = QHBoxLayout()
        self.num_task_layout = QFormLayout()
        self.info_layout = QVBoxLayout()
        self.machine_stats_layout = QVBoxLayout()
        self.table_widget = QTableWidget()
        self.cols = ["Trạng thái", "Khởi tạo", "Cập nhật", "Người tạo", "Type", "CPU Usage", "RAM Usage", "Thực thi", "ETA", "", ""]
        self.table_widget.setColumnCount(len(self.cols))  # Number of columns to display
        self.table_widget.setHorizontalHeaderLabels(self.cols)
        self.table_widget.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table_widget.horizontalHeader().setStretchLastSection(True)

        self.num_task_header = HeaderLabel("TASK STATISTICAL")
        self.num_task_header.setStyleSheet(f"font-size: 15pt; font-weight: bold; color: white;")
        self.num_waiting_header = HeaderLabel(StatusValue.WAITING.value)
        self.num_waiting_header.setStyleSheet(f"font-size: 14pt; font-weight: bold; color: {status_colors[StatusValue.WAITING.value].name()};")
        self.num_waiting_value = HeaderLabel("0")
        self.num_running_header = HeaderLabel(StatusValue.RUNNING.value)
        self.num_running_header.setStyleSheet(f"font-size: 14pt; font-weight: bold; color: {status_colors[StatusValue.RUNNING.value].name()};")
        self.num_running_value = HeaderLabel("0")
        self.num_finished_header = HeaderLabel(StatusValue.FINISHED.value)
        self.num_finished_value = HeaderLabel("0")
        self.num_finished_header.setStyleSheet(f"font-size: 14pt; font-weight: bold; color: {status_colors[StatusValue.FINISHED.value].name()};")
        self.num_error_header = HeaderLabel("KILLED/ERROR")
        self.num_error_header.setStyleSheet(f"font-size: 14pt; font-weight: bold; color: {status_colors[StatusValue.KILLED.value].name()};")
        self.num_error_value = HeaderLabel("0")
        self.num_task_layout.addRow(self.num_task_header, QLabel())
        self.num_task_layout.addRow(self.num_waiting_header, self.num_waiting_value)
        self.num_task_layout.addRow(self.num_running_header, self.num_running_value)
        self.num_task_layout.addRow(self.num_finished_header, self.num_finished_value)
        self.num_task_layout.addRow(self.num_error_header, self.num_error_value)
        self.num_task_layout.setSpacing(10)
        
        self.num_task_widget = QWidget()
        self.num_task_widget.setStyleSheet("background-color: rgba(0, 0, 0, 0);")
        self.num_task_widget.setLayout(self.num_task_layout)
        self.num_task_widget.setFixedSize(200, 150)
        self.info_layout.addWidget(self.num_task_widget)
        # self.info_layout.addLayout(self.num_task_layout)
        
        self.current_system_cpu_percent = 0
        self.current_system_ram_percent = 0

        self.top_layout.addLayout(self.info_layout)
        self.system_monitor = SystemMonitor()
        self.system_monitor.signal_cpu_percent_updated.connect(self.update_current_system_cpu)
        self.system_monitor.signal_ram_percent_updated.connect(self.update_current_system_ram)
        self.top_layout.addStretch(1)
        self.top_layout.addWidget(self.system_monitor)

        self.main_layout.addLayout(self.top_layout)
        self.main_layout.addWidget(self.table_widget)

        self.setLayout(self.main_layout)
        self.showMaximized()
        
        self.command_dict = self.read_module_command_dict(self.config_file, "modules")
        if self.command_dict is None:
            QMessageBox.warning(self, "Error read module command", f"No section \"modules\" in {self.config_file} file, need to define it to call module for task processing")
            sys.exit(1)

        self.list_task = self.db.get_tasks(limit=self.task_limit)
        self.list_task_widget = []
        for index, task in enumerate(self.list_task):
            task_widget = TaskItem(task)
            self.add_task_widget(task_widget, index)

        self.adjust_column_widths()
        self.populate_table()
        
        # realtime update task in database
        self.update_task_from_db_timer = QTimer(self)
        self.update_task_from_db_timer.timeout.connect(self.update_list_task_from_db)
        self.update_task_from_db_timer.start(1000)
        
        # auto start process by process queue
        self.auto_serve_waiting_tasks_timer = QTimer(self)
        self.auto_serve_waiting_tasks_timer.timeout.connect(self.serve_waiting_tasks)  
        self.auto_serve_waiting_tasks_timer.start(2000)
    
    def serve_waiting_tasks(self):
        need_to_update_queue = True
        
        for task_widget in self.list_task_widget:
            if task_widget.task.task_stat == -1: # serve task that in first queue
                
                # if have task with stat = -1 dont update queue if this task not served
                need_to_update_queue = False
                
                serve_this_task = True
                # TODO: Check current resource and decide to serve this task
                # We need to consider usage resoure by task type, difference of each task
                # It's to hard and need mode research for good policy of serve task
                # ex: simple check if current CPU and RAM usage is less then 80%
                if self.current_system_cpu_percent > 60 or self.current_system_ram_percent > 60:
                    print("=========== IGNORE SERVER TASK BECAUSE OF LESS RESOURCE ===========")
                    serve_this_task = False
                
                # If serve a task, need to update queue
                if serve_this_task:
                    print(f"Serve task with id: {task_widget.task.id} - Name: {task_widget.task.creator}")
                    task_widget.start_process()
                    need_to_update_queue = True
                    # only serve one task when call serve_waiting_tasks function 
                    # it prevent serve case that server multi task at the same time, can cause machine overload
                    break  
        
        # if this task was served, increase others queue
        if need_to_update_queue:
            for task_widget in self.list_task_widget:
                task_widget.increase_waiting_queue_position()
        
        
    def update_current_system_ram(self, value):
        self.current_system_ram_percent = value
    
    def update_current_system_cpu(self, value):
        self.current_system_cpu_percent = value
    
    def add_task_widget(self, task_widget: TaskItem, index=-1): # default to end of list
        command = self.command_dict.get(str(int(task_widget.task.type)), "")
        full_command = f"{command} --avt_task_id {task_widget.task.id} --config_file {self.config_file}" 
        # print("Set task command: ", full_command)
        task_widget.update_task_command(full_command)
        # connect signal slot for task changed here
        task_widget.signal_status_changed.connect(self.update_task_statictics)
        print("Size of task widget: ", sys.getsizeof(task_widget))
        
        self.list_task_widget.insert(index, task_widget)        
        
    def update_list_task_from_db(self):
        new_task_list = self.db.get_tasks(limit=self.task_limit)
        
        # Create sets for comparison
        current_task_ids = {task.id for task in self.list_task}
        new_task_ids = {task.id for task in new_task_list}
        
        # Tasks to add
        tasks_to_add = [task for task in new_task_list if task.id not in current_task_ids]
        
        # Tasks to remove
        tasks_to_remove = [task for task in self.list_task if task.id not in new_task_ids]
        
        if len(tasks_to_remove) > 0:
            print("Removing task" , [task.id for task in tasks_to_remove])
            print("List task id: ", [task.id for task in self.list_task])
            print("List task widget id: ", [task.task.id for task in self.list_task_widget])
        
        # Remove tasks
        for task in tasks_to_remove:
            index = self.list_task.index(task)
            print("index to remove: ", index)
            self.table_widget.removeRow(index)
            self.list_task.remove(task)
            # savely remove task widget
            # got crash when removed widget 
            # TODO: got crash here, need to remove widget to free ram usage, 
            # task_widget size is 136 bytes, calculate size of array 10000 task is ~1.3MB
            # self.list_task_widget = [widget for widget in self.list_task_widget if widget.task.id != task.id]
            # self.list_task_widget.remove(index)
            # print("List task id: ", [task.id for task in self.list_task])
            # print("List task widget id: ", [task.task.id for task in self.list_task_widget])
        

        # Add new tasks to the beginning of the table and lists
        for task in reversed(tasks_to_add):  # Reverse to add to the top
            self.list_task.insert(0, task)
            task_widget = TaskItem(task)  # Assuming TaskItem is correctly defined
            # self.list_task_widget.insert(0, task_widget)
            self.add_task_widget(task_widget, 0)
            self.add_task_to_table(task_widget, self.list_task.index(task))  # Add to the top (row 0)
        
        
        self.update_task_statictics()
        
        # Update task data
        # tasks_to_update = [task for task in new_task_list if task.id in current_task_ids]
        # Dont need to update existing tasks, 
        # task_widget object have it own connection to the database and update itself
    
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
            print(f"Error: The file {config_file} does not exist.")
            return None
        except json.JSONDecodeError:
            print("Error: The file is not a valid JSON.")
            return None
        except Exception as e:
            print(f"An error occurred: {e}")
            return None
    
    def add_task_to_table(self, task_widget: TaskItem, row):
        self.table_widget.insertRow(row)
        self.table_widget.setCellWidget(row, 0, task_widget.status_label)
        self.table_widget.setCellWidget(row, 1, task_widget.create_at_value)
        self.table_widget.setCellWidget(row, 2, task_widget.update_at_value)
        self.table_widget.setCellWidget(row, 3, task_widget.creator_value)
        self.table_widget.setCellWidget(row, 4, task_widget.type_value)
        self.table_widget.setCellWidget(row, 5, task_widget.cpu_usage_progess)
        self.table_widget.setCellWidget(row, 6, task_widget.ram_usage_progess)
        self.table_widget.setCellWidget(row, 7, task_widget.time_excute_value)
        self.table_widget.setCellWidget(row, 8, task_widget.time_remain_value)
        self.table_widget.setCellWidget(row, 9, task_widget.start_process_button)
        self.table_widget.setCellWidget(row, 10, task_widget.kill_process_button)
    
    def adjust_column_widths(self):
        # Set the resize mode for specific columns to Fixed
        self.table_widget.horizontalHeader().setSectionResizeMode(1, QHeaderView.Fixed)
        self.table_widget.horizontalHeader().setSectionResizeMode(2, QHeaderView.Fixed)
        self.table_widget.horizontalHeader().setSectionResizeMode(5, QHeaderView.Fixed)
        self.table_widget.horizontalHeader().setSectionResizeMode(6, QHeaderView.Fixed)
        
        # Adjust the width of CPU Usage and RAM Usage columns
        self.table_widget.setColumnWidth(1, 200)  # Adjusting CPU Usage column width
        self.table_widget.setColumnWidth(2, 200)  # Adjusting RAM Usage column width
        self.table_widget.setColumnWidth(5, 200)  # Adjusting CPU Usage column width
        self.table_widget.setColumnWidth(6, 200)  # Adjusting RAM Usage column width
        
    def update_task_statictics(self):
        # print(task_widget.status)
        self.num_waiting_value.setText(str(sum(1 for task_widget in self.list_task_widget if task_widget.status == StatusValue.WAITING)))
        self.num_running_value.setText(str(sum(1 for task_widget in self.list_task_widget if task_widget.status == StatusValue.RUNNING)))
        self.num_finished_value.setText(str(sum(1 for task_widget in self.list_task_widget if task_widget.status == StatusValue.FINISHED)))
        self.num_error_value.setText(str(sum(1 for task_widget in self.list_task_widget if task_widget.status == StatusValue.KILLED or task_widget.status == StatusValue.ERROR)))
    
    def populate_table(self):
        row_count = len(self.list_task_widget)
        self.table_widget.setRowCount(row_count)
        for row, item_widget  in enumerate(self.list_task_widget):
            self.table_widget.setCellWidget(row, 0, item_widget.status_label)
            self.table_widget.setCellWidget(row, 1, item_widget.create_at_value)
            self.table_widget.setCellWidget(row, 2, item_widget.update_at_value)
            self.table_widget.setCellWidget(row, 3, item_widget.creator_value)
            self.table_widget.setCellWidget(row, 4, item_widget.type_value)
            self.table_widget.setCellWidget(row, 5, item_widget.cpu_usage_progess)
            self.table_widget.setCellWidget(row, 6, item_widget.ram_usage_progess)
            self.table_widget.setCellWidget(row, 7, item_widget.time_excute_value)
            self.table_widget.setCellWidget(row, 8, item_widget.time_remain_value)
            self.table_widget.setCellWidget(row, 9, item_widget.start_process_button)
            self.table_widget.setCellWidget(row, 10, item_widget.kill_process_button)

        self.update_task_statictics()

        # Adjust table widget properties if needed
        self.table_widget.setSizeAdjustPolicy(QTableWidget.AdjustToContents)
        

if __name__ == "__main__":
    import sys

    def load_stylesheet(file_path):
        with open(file_path, 'r') as file:
            return file.read()

    app = QApplication(sys.argv)
    stylesheet = load_stylesheet('stylesheet/SpyBot.qss')
    app.setStyleSheet(stylesheet)

    avt_task = AvtTask(
        created_at=int(datetime.now().timestamp()),
        updated_at=int(datetime.now().timestamp()),
        type=7,
        creator="Thai Hoc",
        task_param="""[{"name": "main_image_file", "value": "/data/tiff-data/quang_ninh_1m.tif"}, {"name": "template_image_file", "value": "/data/tiff-data/template/05_resized.png"}]""",
        task_stat=-1,
        worker_ip="127.0.0.1",
        process_id=0,
        task_eta=3600,
        task_output="",
        task_message=""
    )
    # ui = TaskItem(avt_task)
    ui = Ui_TaskManager()
    ui.show()
    sys.exit(app.exec_())
