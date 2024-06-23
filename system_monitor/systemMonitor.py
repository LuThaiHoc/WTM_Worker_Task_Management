################################################################################
##
# Utpal Kumar
# @Earth Inversion
################################################################################

import sys
import platform
import os
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import (QCoreApplication, QPropertyAnimation, QDate, QDateTime,
                          QMetaObject, QObject, QPoint, QRect, QSize, QTime, QUrl, Qt, QEvent, pyqtSignal)
from PyQt5.QtGui import (QBrush, QColor, QConicalGradient, QCursor, QFont, QFontDatabase,
                         QIcon, QKeySequence, QLinearGradient, QPalette, QPainter, QPixmap, QRadialGradient)
from PyQt5.QtWidgets import *
from PyQt5 import uic
import psutil
import GPUtil
from pynvml import nvmlInit, nvmlDeviceGetHandleByIndex, nvmlDeviceGetTemperature, nvmlDeviceGetName, NVML_TEMPERATURE_GPU

from pyqtgraph import PlotWidget
import pyqtgraph as pg
from pathlib import Path
import numpy as np
from collections import deque


# GLOBALS
counter = 0
jumper = 10
QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True) #enable highdpi scaling
QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True) #use highdpi icons


class SystemMonitor(QMainWindow):
    signal_cpu_percent_updated = pyqtSignal(float)
    signal_ram_percent_updated = pyqtSignal(float)
    def __init__(self):
        QMainWindow.__init__(self)
        # self.ui = Ui_MainWindow()
        # self.ui.setupUi(self)
        self.ui = uic.loadUi("./system_monitor/main.ui", self)
        # self.ui = uic.loadUi("./main.ui", self)
        self.cpu_percent = 0
        self.ram_percent = 0
        self.vram_percent = 0
        self.cpu_temp = 0
        self.gpu_temp = 0
        self.traces = dict()
        self.timestamp = 0
        self.timeaxis = []
        self.cpuaxis = []
        self.ramaxis = []
        # self.csv_file = open(datafile, 'w')
        # self.csv_writer = csv.writer(self.csv_file, delimiter=',')
        self.current_timer_cpu_graph = None
        self.current_timer_ram_graph = None
        self.current_timer_vram_graph = None
        self.graph_lim = 15
        self.deque_timestamp = deque([], maxlen=self.graph_lim+20)
        self.deque_cpu = deque([], maxlen=self.graph_lim+20)
        self.deque_ram = deque([], maxlen=self.graph_lim+20)
        self.deque_vram = deque([], maxlen=self.graph_lim+20)
        self.ui.label.setText(
            f"{platform.system()} {platform.machine()}")
        self.ui.label_2.setText(
            f"Processor: {platform.processor()}")
        self.ui.label_3.setText(f"CPUs: {str(psutil.cpu_count(logical=True))}")
        self.ui.label_4.setText(f"RAM: {str(psutil.virtual_memory().total // (1024 ** 2))} MB")

        self.graphwidget1 = PlotWidget(title="CPU percent")
        x1_axis = self.graphwidget1.getAxis('bottom')
        x1_axis.setLabel(text='Time since start (s)')
        y1_axis = self.graphwidget1.getAxis('left')
        y1_axis.setLabel(text='Percent')

        self.graphwidget2 = PlotWidget(title="RAM percent")
        x2_axis = self.graphwidget2.getAxis('bottom')
        x2_axis.setLabel(text='Time since start (s)')
        y2_axis = self.graphwidget2.getAxis('left')
        y2_axis.setLabel(text='Percent')
        
        self.graphwidget3 = PlotWidget(title="VRAM percent")
        x3_axis = self.graphwidget3.getAxis('bottom')
        x3_axis.setLabel(text='Time since start (s)')
        y3_axis = self.graphwidget3.getAxis('left')
        y3_axis.setLabel(text='Percent')
        

        self.btnShowGraphCPU.clicked.connect(self.show_cpu_graph)
        self.btnShowGraphRAM.clicked.connect(self.show_ram_graph)
        self.btnShowGraphVRAM.clicked.connect(self.show_vram_graph)
        self.ui.gridLayout.addWidget(self.graphwidget1, 0, 0, 1, 3)
        self.ui.gridLayout.addWidget(self.graphwidget2, 0, 0, 1, 3)
        self.ui.gridLayout.addWidget(self.graphwidget3, 0, 0, 1, 3)
        self.show_cpu_graph()
        # self.show_ram_graph()
        nvmlInit()
        gpus = GPUtil.getGPUs()
        if gpus:
            gpu = gpus[0]
            self.ui.label_5.setText(f"GPU: {gpu.name}")
            self.ui.label_6.setText(f"VRAM: {int(gpu.memoryTotal)} MB")
        else:
            self.ui.label_5.setText("No GPU")
            self.ui.label_6.setText("")
            
        self.current_timer_systemStat = QtCore.QTimer()
        self.current_timer_systemStat.timeout.connect(
            self.getsystemStatpercent)
        self.current_timer_systemStat.start(1000)
        # self.show_cpu_graph()

    def getsystemStatpercent(self):
        # gives a single float value
        self.cpu_percent = psutil.cpu_percent()
        self.ram_percent = psutil.virtual_memory().percent
        self.cpu_temp = psutil.sensors_temperatures()['coretemp'][0].current 
        # GPU
        gpus = GPUtil.getGPUs()
        if gpus:
            gpu = gpus[0]  # Assuming we're interested in the first GPU
            handle = nvmlDeviceGetHandleByIndex(0)
            self.gpu_temp = nvmlDeviceGetTemperature(handle, NVML_TEMPERATURE_GPU)
            self.vram_percent = gpu.load * 100
        else:
            self.gpu_temp = None
            self.vram_percent = None

        
        self.signal_cpu_percent_updated.emit(self.cpu_percent)
        self.signal_ram_percent_updated.emit(self.ram_percent)
        
        if self.gpu_temp is not None:
            self.ui.labelTempGPU.setText(f"{self.gpu_temp:.1f}c")
        if self.vram_percent is not None:
            self.setValue(self.vram_percent, self.ui.labelPercentageVRAM,
                      self.ui.circularProgressVRAM, "rgba(191, 191, 88, 255)")
            
        self.ui.labelTempCPU.setText(f"{self.cpu_temp:.1f}c")
        self.setValue(self.cpu_percent, self.ui.labelPercentageCPU,
                      self.ui.circularProgressCPU, "rgba(85, 170, 255, 255)")
        self.setValue(self.ram_percent, self.ui.labelPercentageRAM,
                      self.ui.circularProgressRAM, "rgba(255, 0, 127, 255)")

    def start_cpu_graph(self):
        # self.timeaxis = []
        # self.cpuaxis = []
        if self.current_timer_cpu_graph:
            self.current_timer_cpu_graph.stop()
            self.current_timer_cpu_graph.deleteLater()
            self.current_timer_cpu_graph = None
        self.current_timer_cpu_graph = QtCore.QTimer()
        self.current_timer_cpu_graph.timeout.connect(self.update_cpu)
        self.current_timer_cpu_graph.start(1000)

    def update_cpu(self):
        self.timestamp += 1

        self.deque_timestamp.append(self.timestamp)
        self.deque_cpu.append(self.cpu_percent)
        self.deque_ram.append(self.ram_percent)
        self.deque_vram.append(self.vram_percent)
        timeaxis_list = list(self.deque_timestamp)
        cpu_list = list(self.deque_cpu)

        if self.timestamp > self.graph_lim:
            self.graphwidget1.setRange(xRange=[self.timestamp-self.graph_lim+1, self.timestamp], yRange=[
                                       min(cpu_list[-self.graph_lim:]), max(cpu_list[-self.graph_lim:])])
        self.set_plotdata(name="cpu", data_x=timeaxis_list,
                          data_y=cpu_list)

    def start_ram_graph(self):

        if self.current_timer_ram_graph:
            self.current_timer_ram_graph.stop()
            self.current_timer_ram_graph.deleteLater()
            self.current_timer_ram_graph = None
        self.current_timer_ram_graph = QtCore.QTimer()
        self.current_timer_ram_graph.timeout.connect(self.update_ram)
        self.current_timer_ram_graph.start(1000)

    def update_ram(self):
        self.timestamp += 1

        self.deque_timestamp.append(self.timestamp)
        self.deque_cpu.append(self.cpu_percent)
        self.deque_ram.append(self.ram_percent)
        self.deque_vram.append(self.vram_percent)
        timeaxis_list = list(self.deque_timestamp)
        ram_list = list(self.deque_ram)
        
        if self.timestamp > self.graph_lim:
            self.graphwidget2.setRange(xRange=[self.timestamp-self.graph_lim+1, self.timestamp], yRange=[
                                       min(ram_list[-self.graph_lim:]), max(ram_list[-self.graph_lim:])])
        self.set_plotdata(name="ram", data_x=timeaxis_list,
                          data_y=ram_list)
        
    
    def start_vram_graph(self):

        if self.current_timer_vram_graph:
            self.current_timer_vram_graph.stop()
            self.current_timer_vram_graph.deleteLater()
            self.current_timer_vram_graph = None
        self.current_timer_vram_graph = QtCore.QTimer()
        self.current_timer_vram_graph.timeout.connect(self.update_vram)
        self.current_timer_vram_graph.start(1000)
    
    def update_vram(self):
        self.timestamp += 1

        self.deque_timestamp.append(self.timestamp)
        self.deque_cpu.append(self.cpu_percent)
        self.deque_ram.append(self.ram_percent)
        self.deque_vram.append(self.vram_percent)
        timeaxis_list = list(self.deque_timestamp)
        vram_list = list(self.deque_vram)
        

        if self.timestamp > self.graph_lim:
            self.graphwidget3.setRange(xRange=[self.timestamp-self.graph_lim+1, self.timestamp], yRange=[
                                       min(vram_list[-self.graph_lim:]), max(vram_list[-self.graph_lim:])])
        self.set_plotdata(name="vram", data_x=timeaxis_list,
                          data_y=vram_list)

    def show_cpu_graph(self):
        self.graphwidget2.hide()
        self.graphwidget3.hide()
        self.graphwidget1.show()
        self.start_cpu_graph()
        self.btnShowGraphCPU.setEnabled(False)
        self.btnShowGraphRAM.setEnabled(True)
        self.btnShowGraphVRAM.setEnabled(True)
        
        self.btnShowGraphCPU.setStyleSheet(
            "QPushButton" "{" "background-color : lightblue;" "}"
        )
        self.btnShowGraphRAM.setStyleSheet(
            "QPushButton"
            "{"
            "background-color : rgb(255, 44, 174);"
            "}"
            "QPushButton"
            "{"
            "color : white;"
            "}"
        )
        self.btnShowGraphVRAM.setStyleSheet(
            "QPushButton"
            "{"
            "background-color : rgb(191, 191, 88);"
            "}"
            "QPushButton"
            "{"
            "color : white;"
            "}"
        )

    def show_ram_graph(self):
        self.graphwidget1.hide()
        self.graphwidget2.show()
        self.graphwidget3.hide()
        # self.graphwidget2.autoRange()
        self.start_ram_graph()
        self.btnShowGraphRAM.setEnabled(False)
        self.btnShowGraphCPU.setEnabled(True)
        self.btnShowGraphVRAM.setEnabled(True)
        self.btnShowGraphRAM.setStyleSheet(
            "QPushButton" "{" "background-color : lightblue;" "}"
        )
        self.btnShowGraphCPU.setStyleSheet(
            "QPushButton"
            "{"
            "background-color : rgba(85, 170, 255, 255);"
            "}"
            "QPushButton"
            "{"
            "color : white;"
            "}"
        )
        self.btnShowGraphVRAM.setStyleSheet(
            "QPushButton"
            "{"
            "background-color : rgba(191, 191, 88, 255);"
            "}"
            "QPushButton"
            "{"
            "color : white;"
            "}"
        )
        
    def show_vram_graph(self):
        
        self.graphwidget1.hide()
        self.graphwidget2.hide()
        self.graphwidget3.show()
        # self.graphwidget2.autoRange()
        self.start_vram_graph()
        self.btnShowGraphVRAM.setEnabled(False)
        self.btnShowGraphRAM.setEnabled(True)
        self.btnShowGraphCPU.setEnabled(True)
        self.btnShowGraphVRAM.setStyleSheet(
            "QPushButton" "{" "background-color : lightblue;" "}"
        )
        self.btnShowGraphCPU.setStyleSheet(
            "QPushButton"
            "{"
            "background-color : rgba(85, 170, 255, 255);"
            "}"
            "QPushButton"
            "{"
            "color : white;"
            "}"
        )
        self.btnShowGraphRAM.setStyleSheet(
            "QPushButton"
            "{"
            "background-color : rgb(255, 44, 174);"
            "}"
            "QPushButton"
            "{"
            "color : white;"
            "}"
        )

    def set_plotdata(self, name, data_x, data_y):
        # print('set_data')
        if name in self.traces:
            self.traces[name].setData(data_x, data_y)
        else:
            if name == "cpu":
                self.traces[name] = self.graphwidget1.getPlotItem().plot(
                    pen=pg.mkPen((85, 170, 255), width=3))

            elif name == "ram":
                self.traces[name] = self.graphwidget2.getPlotItem().plot(
                    pen=pg.mkPen((255, 0, 127), width=3))
            
            elif name == "vram":
                self.traces[name] = self.graphwidget3.getPlotItem().plot(
                    pen=pg.mkPen((196, 196, 88), width=3))

    # ==> SET VALUES TO DEF progressBarValue

    def setValue(self, value, labelPercentage, progressBarName, color):

        sliderValue = value

        # HTML TEXT PERCENTAGE
        htmlText = """<p align="center"><span style=" font-size:40pt;">{VALUE}</span><span style=" font-size:35pt; vertical-align:super;">%</span></p>"""
        labelPercentage.setText(htmlText.replace(
            "{VALUE}", f"{sliderValue:.1f}"))

        # CALL DEF progressBarValue
        self.progressBarValue(sliderValue, progressBarName, color)

    # DEF PROGRESS BAR VALUE
    ########################################################################

    def progressBarValue(self, value, widget, color):

        # PROGRESSBAR STYLESHEET BASE
        styleSheet = """
        QFrame{
        	border-radius: 110px;
        	background-color: qconicalgradient(cx:0.5, cy:0.5, angle:90, stop:{STOP_1} rgba(255, 0, 127, 0), stop:{STOP_2} {COLOR});
        }
        """

        # GET PROGRESS BAR VALUE, CONVERT TO FLOAT AND INVERT VALUES
        # stop works of 1.000 to 0.000
        progress = (100 - value) / 100.0

        # GET NEW VALUES
        stop_1 = str(progress - 0.001)
        stop_2 = str(progress)

        # FIX MAX VALUE
        if value == 100:
            stop_1 = "1.000"
            stop_2 = "1.000"

        # SET VALUES TO NEW STYLESHEET
        newStylesheet = styleSheet.replace("{STOP_1}", stop_1).replace(
            "{STOP_2}", stop_2).replace("{COLOR}", color)

        # APPLY STYLESHEET WITH NEW VALUES
        widget.setStyleSheet(newStylesheet)


# ==> SPLASHSCREEN WINDOW
class SplashScreen(QMainWindow):
    def __init__(self):
        QMainWindow.__init__(self)
        # self.ui = Ui_SplashScreen()
        # self.ui.setupUi(self)
        self.ui = uic.loadUi("./system_monitor/splash_screen.ui", self)
        # self.ui = uic.loadUi("./splash_screen.ui", self)
        # ==> SET INITIAL PROGRESS BAR TO (0) ZERO
        self.progressBarValue(0)

        # ==> REMOVE STANDARD TITLE BAR
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint)  # Remove title bar
        # Set background to transparent
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)

        # ==> APPLY DROP SHADOW EFFECT
        self.shadow = QGraphicsDropShadowEffect(self)
        self.shadow.setBlurRadius(20)
        self.shadow.setXOffset(0)
        self.shadow.setYOffset(0)
        self.shadow.setColor(QColor(0, 0, 0, 120))
        self.ui.circularBg.setGraphicsEffect(self.shadow)

        # QTIMER ==> START
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.progress)
        # TIMER IN MILLISECONDS
        self.timer.start(15)

        # SHOW ==> MAIN WINDOW
        ########################################################################
        self.show()
        ## ==> END ##

    # DEF TO LOANDING
    ########################################################################
    def progress(self):
        global counter
        global jumper
        value = counter

        # HTML TEXT PERCENTAGE
        htmlText = """<p><span style=" font-size:68pt;">{VALUE}</span><span style=" font-size:58pt; vertical-align:super;">%</span></p>"""

        # REPLACE VALUE
        newHtml = htmlText.replace("{VALUE}", str(jumper))

        if(value > jumper):
            # APPLY NEW PERCENTAGE TEXT
            self.ui.labelPercentage.setText(newHtml)
            jumper += 10

        # SET VALUE TO PROGRESS BAR
        # fix max value error if > than 100
        if value >= 100:
            value = 1.000
        self.progressBarValue(value)
        if counter == 10:
            self.main = SystemMonitor()

        # CLOSE SPLASH SCREE AND OPEN APP
        if counter > 100:
            # STOP TIMER
            self.timer.stop()

            # SHOW MAIN WINDOW
            # self.main = SystemMonitor()
            self.main.show()

            # CLOSE SPLASH SCREEN
            self.close()

        # INCREASE COUNTER
        counter += 0.5

    # DEF PROGRESS BAR VALUE
    ########################################################################
    def progressBarValue(self, value):

        # PROGRESSBAR STYLESHEET BASE
        styleSheet = """
        QFrame{
        	border-radius: 150px;
        	background-color: qconicalgradient(cx:0.5, cy:0.5, angle:90, stop:{STOP_1} rgba(255, 0, 127, 0), stop:{STOP_2} rgba(85, 170, 255, 255));
        }
        """

        # GET PROGRESS BAR VALUE, CONVERT TO FLOAT AND INVERT VALUES
        # stop works of 1.000 to 0.000
        progress = (100 - value) / 100.0

        # GET NEW VALUES
        stop_1 = str(progress - 0.001)
        stop_2 = str(progress)

        # SET VALUES TO NEW STYLESHEET
        newStylesheet = styleSheet.replace(
            "{STOP_1}", stop_1).replace("{STOP_2}", stop_2)

        # APPLY STYLESHEET WITH NEW VALUES
        self.ui.circularProgress.setStyleSheet(newStylesheet)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = SplashScreen()
    sys.exit(app.exec_())
