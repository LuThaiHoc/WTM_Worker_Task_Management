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
import threading
import time
import psutil

status_colors = {
    "WAITING": QColor(255, 255, 0),    # Yellow
    "RUNNING": QColor(0, 255, 0),      # Green
    "FINISHED": QColor(0, 0, 255),     # Blue
    "KILLED": QColor(255, 0, 0),       # Red
    "ERROR": QColor(255, 165, 0)       # Orange
}

task_types = {
    1 : "Correction",
    2 : "Pre-Process",
    3 : "Cloud removed",
    4 : "Enhancement",
    5 : "Detection",
    6 : "Classification",
    7 : "Object finder",
    8 : "Others"
}

class StatusValue(Enum):
    WAITING = "WAITING"
    RUNNING = "RUNNING"
    FINISHED = "FINISHED"
    KILLED = "KILLED"
    ERROR = "ERROR"

def format_timestamp(timestamp_int):
    try:
        # Convert the integer timestamp to a datetime object
        dt_object = datetime.fromtimestamp(int(timestamp_int/1000))
        # Format the datetime object to the desired format
        formatted_time = dt_object.strftime('%H:%M:%S %d-%m-%Y')
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

class Ui_TaskItem(QWidget):
    signal_status_changed = pyqtSignal()
    
    def __init__(self, task_data: AvtTask):
        super().__init__()
        self.task = task_data
        
        self.main_layout = QHBoxLayout()
        self.grid_layout = QGridLayout()
        
        self.status_layout = QHBoxLayout()
        self.status = StatusValue.RUNNING
        self.status_label = QLabel("")
        self.status_label.setFixedWidth(100)
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_layout.addWidget(self.status_label)
        
        self.create_at_header = HeaderLabel("Khởi tạo:")
        self.create_at_value = ValueLabel(format_timestamp(self.task.createdAt))
        self.update_at_header = HeaderLabel("Cập nhật:")
        self.update_at_value = ValueLabel(format_timestamp(self.task.updatedAt))
        self.creator_header = HeaderLabel("Người tạo:")
        self.creator_value = ValueLabel(self.task.creator)
        self.type_header = HeaderLabel("Type:")
        self.type_value = ValueLabel(task_types[self.task.type])
        
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
        self.time_remain_value = ValueLabel(f"{str(self.task.task_ETA)}s")
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
        
        self.update_task_status(self.get_status_by_stat())
        self.start_process_button.clicked.connect(self.start_process)
        self.kill_process_button.clicked.connect(self.kill_process)
        
        command = "python /media/hoc/WORK/remote/AnhPhuong/SAT/Project/SAT_Modules/template_matching/main.py"
        self.process_monitor = ProcessMonitor(command)
        self.process_monitor.signal_process_started.connect(self.process_started)
        self.process_monitor.signal_process_ended.connect(self.process_ended)
        self.process_monitor.signal_process_killed.connect(self.process_killed)
        self.process_monitor.signal_running_time_update.connect(self.update_running_time)
        self.process_monitor.signal_process_cpu_usage_update.connect(self.update_cpu_usage)
        self.process_monitor.signal_process_ram_usage_update.connect(self.update_ram_usage)
    
    def update_task_data(self, task: AvtTask):
        self.task = task
        # self.create_at_value.setText(format_timestamp(self.task.createdAt))
        self.update_at_value.setText(format_timestamp(self.task.updatedAt))
        # self.creator_value.setText(self.task.creator)
        # self.type_value.setText(task_types[self.task.type])
        self.time_remain_value.setText(f"{str(self.task.task_ETA)}s")
    
    def update_running_time(self, value):
        self.time_excute_value.setText(f"{value}s")
        
    def process_killed(self):
        # update stats to database
        
        # update status
        self.update_task_status(StatusValue.KILLED)
    
    def process_ended(self):
        # update stats to database
        
        # update status
        self.update_task_status(StatusValue.FINISHED)
    
    def process_started(self):
        # set stats to database
        
        # update status
        self.update_task_status(StatusValue.RUNNING)
    
    def update_ram_usage(self, usage):
        formatted_usage = f"{usage:.2f} MB"
        self.ram_usage_progess.setValue(int(usage))
        self.ram_usage_progess.setFormat(formatted_usage)
    
    def update_cpu_usage(self, usage):
        self.cpu_usage_progess.setValue(int(usage))   
             
    def get_status_by_stat(self) -> StatusValue:
        stat = self.task.task_stat
        if stat < 0:
            return StatusValue.WAITING
        elif stat == 0:
            return StatusValue.ERROR # also killed status
        elif stat == 1:
            return StatusValue.FINISHED
        elif stat > 1:
            return StatusValue.RUNNING
        
    def kill_process(self):
        # kill process...
        self.process_monitor.kill_process()
        # self.update_task_status(StatusValue.KILLED)
    
    def start_process(self):
        print("Start process...")
        # start process
        self.process_monitor.start_process()
        # monitor process
        # self.monitoring_process_thread = threading.Thread(target=self.process_monitor.monitor_process)
        # self.monitoring_process_thread.start()

        # self.update_task_status(StatusValue.RUNNING)
        
    def update_task_status(self, new_status : StatusValue):
        self.status = new_status
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
            
        self.signal_status_changed.emit()
        

from system_monitor.systemMonitor import SystemMonitor
class Ui_TaskManager(QWidget):
    def __init__(self):
        super().__init__()
        db_config = DatabaseConfig().read_from_json("config.json")
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
        self.num_task_widget.setFixedSize(300, 150)
        self.info_layout.addWidget(self.num_task_widget)
        # self.info_layout.addLayout(self.num_task_layout)
        

        self.top_layout.addLayout(self.info_layout)
        self.system_monitor = SystemMonitor()
        self.top_layout.addStretch(1)
        self.top_layout.addWidget(self.system_monitor)

        self.main_layout.addLayout(self.top_layout)
        self.main_layout.addWidget(self.table_widget)

        self.setLayout(self.main_layout)
        self.showMaximized()

        self.list_task = self.db.get_tasks(limit=5)
        self.list_task_widget = [Ui_TaskItem(task) for task in self.list_task]
        
        self.adjust_column_widths()
        self.populate_table()
        
        # realtime update task in database
        self.update_task_from_db_timer = QTimer()
        self.update_task_from_db_timer.timeout.connect(self.update_list_task_from_db)
        self.update_task_from_db_timer.start(1000)
        
    def update_list_task_from_db(self):
        new_task_list = self.db.get_tasks(limit=5)
        
        # Create sets for comparison
        current_task_ids = {task.id for task in self.list_task}
        new_task_ids = {task.id for task in new_task_list}
        
        # Tasks to add
        tasks_to_add = [task for task in new_task_list if task.id not in current_task_ids]
        
        # Tasks to remove
        tasks_to_remove = [task for task in self.list_task if task.id not in new_task_ids]
        if len(tasks_to_remove) > 0:
            print([task.id for task in tasks_to_remove])
        
        # Tasks to update
        tasks_to_update = [task for task in new_task_list if task.id in current_task_ids]
        
        # Remove tasks
        for task in tasks_to_remove:
            index = self.list_task.index(task)
            print("index to remove: ", index)
            self.table_widget.removeRow(index)
            self.list_task.remove(task)
            # savely remove task widget
            # got crash when removed widget 
            # TODO: need to remove widget to reduce ram usage, got crash here!
            # self.list_task_widget = [widget for widget in self.list_task_widget if widget.task.id != task.id]
            # self.list_task_widget.pop(index)
        
        # # Add new tasks
        # for task in tasks_to_add:
        #     self.list_task.append(task)
        #     task_widget = Ui_TaskItem(task)
        #     self.list_task_widget.append(task_widget)
        #     self.add_task_to_table(task_widget)
            
        # Add new tasks to the beginning of the table and lists
        for task in reversed(tasks_to_add):  # Reverse to add to the top
            self.list_task.insert(0, task)
            task_widget = Ui_TaskItem(task)  # Assuming Ui_TaskItem is correctly defined
            self.list_task_widget.insert(0, task_widget)
            self.add_task_to_table(task_widget, 0)  # Add to the top (row 0)
        
        # Update existing tasks
        # for task in tasks_to_update:
        #     index = self.list_task.index(task)
        #     self.list_task[index] = task
        #     task_widget = self.list_task_widget[index]
        #     task_widget.update_task_data(task)
        
        # Update the counts in the header labels
        self.update_header_counts()
        
    def update_header_counts(self):
        self.num_waiting_value.setText(str(sum(1 for task in self.list_task if task.task_stat < 0)))
        self.num_running_value.setText(str(sum(1 for task in self.list_task if task.task_stat > 1)))
        self.num_finished_value.setText(str(sum(1 for task in self.list_task if task.task_stat == 1)))
        self.num_error_value.setText(str(sum(1 for task in self.list_task if task.task_stat == 0)))

    
    def add_task_to_table(self, task_widget: Ui_TaskItem, row):
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
        
    def populate_table(self):
        row_count = len(self.list_task)
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

        # Update the counts in the header labels
        self.num_waiting_value.setText(str(sum(1 for task in self.list_task if task.task_stat < 0)))
        self.num_running_value.setText(str(sum(1 for task in self.list_task if task.task_stat > 1)))
        self.num_finished_value.setText(str(sum(1 for task in self.list_task if task.task_stat == 1)))
        self.num_error_value.setText(str(sum(1 for task in self.list_task if task.task_stat == 0)))

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
        createdAt=int(datetime.now().timestamp()),
        updatedAt=int(datetime.now().timestamp()),
        type=7,
        creator="Thai Hoc",
        task_param="""[{"name": "main_image_file", "value": "/data/tiff-data/quang_ninh_1m.tif"}, {"name": "template_image_file", "value": "/data/tiff-data/template/05_resized.png"}]""",
        task_stat=-1,
        worker_ip="127.0.0.1",
        process_id=0,
        task_ETA=3600,
        task_output="",
        task_message=""
    )
    # ui = Ui_TaskItem(avt_task)
    ui = Ui_TaskManager()
    ui.show()
    sys.exit(app.exec_())
