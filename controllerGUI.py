import qdarkstyle
from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QIcon
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import numpy as np
import serial
from serial.tools import list_ports
import sys
import time
import matplotlib.image as mpimg

matplotlib.use('Qt5Agg')

class ComboBox(QComboBox):
    popupAboutToBeShown = pyqtSignal()

    def showPopup(self):
        self.popupAboutToBeShown.emit()
        super(ComboBox, self).showPopup()

class PlotCanvas(FigureCanvas):

    def __init__(self, parent=None, width=10, height=8, dpi=100):

        self.fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = self.fig.add_subplot(111)

        FigureCanvas.__init__(self, self.fig)
        self.setParent(parent)

        FigureCanvas.setSizePolicy(self,
                QSizePolicy.Expanding,
                QSizePolicy.Expanding)
        FigureCanvas.updateGeometry(self)

    def plot(self, x, y, color, variable_name):

        ax = self.fig.add_subplot(111)
        ax.plot(x, y, color = color, label = variable_name)
        ax.set_xlabel("Time")
        ax.set_ylabel("PWM Signal")
        plt.grid('on')
        ax.legend()
        self.draw()

    def show_image(self, img):

        self.fig.patch.set_facecolor('lightcyan')
        self.imCanvas = FigureCanvas(self.fig)
        self.axes.imshow(img)

    def clear(self):

        self.fig.clf()

class Window(QMainWindow): 
 
    def __init__(self):

        super().__init__()
        self.setGeometry(250, 250, 800, 600) 
        self.setWindowTitle("APP")
        self.setWindowIcon(QIcon('kahvelab.png'))
        self.tabWidget()
        self.Widgets()
        self.layouts()
        self.init_variables()
        self.show()

    def tabWidget(self):

        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)
        self.tab1 = QWidget()
        self.tabs.addTab(self.tab1, "RF SWITCH")
    
    def init_variables(self):

        self.pwm_list = [0 for _ in range(100)]
        self.freq = 0
        self.duty_cycle = 0
        self.baud_rate = 0
        self.com = ""
        self.on_time = 0
        self.off_time = 0

    def Widgets(self):

        self.pltObj = PlotCanvas(self)

        self.baudrate_list_qlabel = QLabel("Baud Rate")
        self.baudrate_cb = QComboBox(self)
        self.baudrate_cb.addItems(["----------", "300", "600", "1200", "2400", 
                                   "4800", "9600", "14400", "19200", 
                                   "28800", "38400", "56000", "57600", 
                                   "115200", "128000", "256000"])
        self.baudrate_cb.currentTextChanged.connect(self.baudrate_clicked_func)

        self.on_time_qlabel = QLabel("Enter ON TIME(us)", self)
        self.on_txtbox = QLineEdit(self)
        self.on_button = QPushButton("OK", self)
        self.on_button.clicked.connect(self.on_time_func)

        self.off_time_qlabel = QLabel("Enter OFF TIME(us)", self)
        self.off_time_txtbox = QLineEdit(self)
        self.off_time_button = QPushButton("OK", self)
        self.off_time_button.clicked.connect(self.off_time_func)
        
        self.com_qlabel = QLabel("Enter COM", self)
        self.com_cb = ComboBox(self)
        self.com_cb.addItem("----------")
        self.com_cb.popupAboutToBeShown.connect(self.update_coms_func)

        self.connect_button = QPushButton("Connect", self)
        self.connect_button.clicked.connect(self.connect_MCU)

        self.configure_button = QPushButton("SET PWM", self)
        self.configure_button.clicked.connect(self.set_PWM)

        self.serial_monitor_list =  QListWidget()
        self.serial_monitor_list.addItem("Welcome RF SWITCH GUI!")  

        self.clear_serial_monitor = QPushButton("CLEAR", self)
        self.clear_serial_monitor.clicked.connect(self.clear_list)

        img = mpimg.imread('kahvelab.png')
        self.pltObj.show_image(img)

    def serial_monitor(self, item):

        self.serial_monitor_list.addItem(item)

    def clear_list(self):

        self.serial_monitor_list.clear()

    def on_time_func(self):

        try:
            self.on_time = float(self.on_txtbox.text()) * 1E-6
            print(self.on_time)
        except:
            info_box = QMessageBox.information(self, "WARNING!", "It is not a valid input!")
            return -1
        
    def off_time_func(self):

        try:
            self.off_time = float(self.off_time_txtbox.text()) * 1E-6
        except:
            info_box = QMessageBox.information(self, "WARNING!", "It is not a valid input!")
            return -1
    
    def receive(self) -> str:

        TERMINATOR = '\r'.encode('UTF8')
        line = self.mcu.read_until(TERMINATOR)
        return line.decode('UTF8').strip()
    
    def send(self, text: str):

        line = '%s\r\f' % text
        self.mcu.write(line.encode('utf-8'))

    def set_PWM(self):

        self.freq = 1/(self.on_time + self.off_time)
        self.duty_cycle = (self.on_time / (self.on_time + self.off_time))*100
        print(self.duty_cycle)
        
        if self.mcu:

            data = str(self.freq) + "-" + str(self.duty_cycle)
            self.send(data)
            self.mcu.flush()
            time.sleep(0.1)
            message = self.receive()
            self.serial_monitor(message)
            self.plot_func()

    def connect_MCU(self):

        self.com = self.com_cb.currentText()
        self.clear_list()

        if self.com != "" and self.baud_rate != 0:

            self.mcu = serial.Serial(self.com, self.baud_rate, timeout = 0.3)
            time.sleep(0.1)
            message = self.receive()
            self.serial_monitor(message)

    def baudrate_clicked_func(self):

        self.baud_rate = int(self.baudrate_cb.currentText())

    def update_coms_func(self):
        
        self.com_cb.clear()
        com_list = list_ports.comports()

        for port in com_list:

            port = str(port)
            port_name = port.split("-")
            self.com_cb.addItem(port_name[0])
        
    def plot_func(self):

        
        self.pwm_list = [1 if int(self.duty_cycle) > count else 0 for count in range(100)]
        self.pltObj.clear()
        self.pltObj.plot(range(0, 100), self.pwm_list, color = "green", variable_name = str(self.freq) + " Hz")
        
    def layouts(self):

        self.main_layout = QHBoxLayout()
        self.right_layout = QFormLayout()
        self.left_layout = QFormLayout()
        self.plot_layout = QVBoxLayout()
        self.left_Hbox1 = QHBoxLayout()
        self.left_Hbox2 = QHBoxLayout()
        self.right_Vbox = QVBoxLayout()

        # Left layout

        self.left_layout_group_box = QGroupBox("")
        self.left_Hbox1.addWidget(self.baudrate_list_qlabel)
        self.left_Hbox1.addWidget(self.baudrate_cb)
        self.left_Hbox1.addStretch()
        self.left_Hbox1.addWidget(self.com_qlabel)
        self.left_Hbox1.addWidget(self.com_cb)
        self.left_Hbox1.addStretch()
        self.left_Hbox1.addWidget(self.connect_button)
        self.left_layout.addRow(self.left_Hbox1)

        self.plot_layout.addWidget(self.pltObj)
        self.left_layout.addRow(self.plot_layout)

        self.left_Hbox2.addWidget(self.on_time_qlabel)
        self.left_Hbox2.addWidget(self.on_txtbox)
        self.left_Hbox2.addWidget(self.on_button)
        self.left_Hbox2.addStretch()
        self.left_Hbox2.addWidget(self.off_time_qlabel)
        self.left_Hbox2.addWidget(self.off_time_txtbox)
        self.left_Hbox2.addWidget(self.off_time_button)
        self.left_Hbox2.addStretch()
        self.left_Hbox2.addWidget(self.configure_button)
        self.left_layout.addRow(self.left_Hbox2) 

        self.left_layout_group_box.setLayout(self.left_layout)

        # Right layout
              
        self.right_layout_group_box = QGroupBox("Serial Monitor")

        self.right_Vbox.addWidget(self.serial_monitor_list) 
        self.right_Vbox.addWidget(self.clear_serial_monitor)   
        self.right_layout.addRow(self.right_Vbox)

        self.right_layout_group_box.setLayout(self.right_layout)


        self.main_layout.addWidget(self.left_layout_group_box, 60)
        self.main_layout.addWidget(self.right_layout_group_box, 40)
        self.tab1.setLayout(self.main_layout)  

def main():

    app = QApplication(sys.argv)
    app.setStyleSheet(qdarkstyle.load_stylesheet()) 
    window = Window()
    sys.exit(app.exec_())

if __name__ == "__main__":

    main()