from PySide import QtCore,QtGui
from PySide import QtUiTools
import os, sys
import glob
from Shiva import Shiva
from serial.serialutil import SerialException
from LevelFeedbackReader import LevelFeedbackReaderListener

def load_ui(file_name, where=None):
    """
    Loads a .UI file into the corresponding Qt Python object
    :param file_name: UI file path
    :param where: Use this parameter to load the UI into an existing class (i.e. to override methods)
    :return: loaded UI
    """
    # Create a QtLoader
    loader = QtUiTools.QUiLoader()

    # Open the UI file
    ui_file = QtCore.QFile(file_name)
    ui_file.open(QtCore.QFile.ReadOnly)

    # Load the contents of the file
    ui = loader.load(ui_file, where)

    # Close the file
    ui_file.close()

    return ui

class ShivaGUI(QtGui.QWidget, LevelFeedbackReaderListener):
    default_baudrate = 9600
    num_channels = 8
    max_resolution = 1024
    feedback_arrived = QtCore.Signal(int, int)

    def __init__(self, parent=None, shiva=None):
        QtGui.QWidget.__init__(self, parent)
        LevelFeedbackReaderListener.__init__(self)

        # Interface to board is required
        self.shiva = shiva
        self.shiva.addFeedbackListener(self)
        self.enabled_channels = [0, 1, 0, 0, 0, 0, 0, 0]

        # Widgets to be created
        self.comboBox = None
        self.lineEdit = None
        self.portButton = None
        self.connectButton = None

        self.channelGroups = []
        self.noteComboBoxes = []
        self.valueBars = []
        self.triggerThresholdSliders = []
        self.offThresholdSliders = []

        self.setupUI()
        self.resetValues()
        self.resetChannelWidgets()

    def setupUI(self):
        ui_file_path = os.path.join(os.path.realpath(os.path.dirname(__file__)), 'Shiva.ui')
        main_widget = load_ui(ui_file_path, self)
        layout = QtGui.QVBoxLayout()
        layout.addWidget(main_widget)
        self.setLayout(layout)

        # Get a reference to all required widgets
        self.comboBox = self.findChild(QtGui.QComboBox, 'comboBox')
        self.lineEdit = self.findChild(QtGui.QLineEdit, 'lineEdit')
        self.portButton = self.findChild(QtGui.QPushButton, 'portButton')
        self.connectButton = self.findChild(QtGui.QPushButton, 'connectButton')

        # Connect widgets to actions
        self.portButton.clicked.connect(self.resetValues)
        self.connectButton.clicked.connect(self.onConnectClicked)

        # Load channels ui
        for i in range(self.num_channels):
            self.loadChannelUI(i)

        self.toggleChannelWidgets(False)


    def loadChannelUI(self, channel_index):
        ui_file_path = os.path.join(os.path.realpath(os.path.dirname(__file__)), 'channel.ui')
        widget = load_ui(ui_file_path)
        layout = self.findChild(QtGui.QLayout, 'gridLayout')

        # Get a reference of all widgets
        self.channelGroups.append(widget.findChild(QtGui.QGroupBox, 'groupBox'))
        self.channelGroups[-1].setTitle("Channel " + str(channel_index))
        self.noteComboBoxes.append(widget.findChild(QtGui.QComboBox, 'noteComboBox'))
        value_bar = widget.findChild(QtGui.QProgressBar, 'valueBar')
        value_bar.setRange(0, self.max_resolution-1)
        self.valueBars.append(value_bar)
        self.triggerThresholdSliders.append(widget.findChild(QtGui.QSlider, 'triggerThresholdSlider'))
        self.offThresholdSliders.append(widget.findChild(QtGui.QSlider, 'offThresholdSlider'))

        # Connect signals
        self.noteComboBoxes[-1].currentIndexChanged.connect(lambda: self.onSoundComboBoxSelectionChanged(channel_index))
        self.feedback_arrived.connect(lambda c, v:self.valueBars[c].setValue(v))
        self.triggerThresholdSliders[-1].sliderReleased.connect(lambda : self.onTriggerThresholdSliderReleased(channel_index))
        self.offThresholdSliders[-1].sliderReleased.connect(lambda : self.onOffThresholdSliderReleased(channel_index))

        layout.addWidget(widget, channel_index/2, channel_index%2)


    def resetValues(self):
        self.lineEdit.setText(str(self.default_baudrate))
        self.comboBox.clear()
        self.comboBox.addItems(self.getSerialPorts())


    def resetChannelWidgets(self):
        # Clear all widgets
        for i in range(self.num_channels):
            #self.channelGroups[i].setChecked(bool(self.enabled_channels[i]))
            self.noteComboBoxes[i].clear()
            self.noteComboBoxes[i].addItems(list(sorted(self.shiva.drums.keys())))
            self.triggerThresholdSliders[i].setMinimum(0)
            self.triggerThresholdSliders[i].setMaximum(self.max_resolution-1)
            self.offThresholdSliders[i].setMinimum(0)
            self.offThresholdSliders[i].setMaximum(self.max_resolution-1)

    def toggleChannelWidgets(self, enable):
        if enable:
            for group, state in zip(self.channelGroups, self.enabled_channels):
                if state == 0:
                    group.setChecked(False)
                else:
                    group.setChecked(True)
        else:
            for group in self.channelGroups:
                group.setChecked(False)

    def onConnectClicked(self):
        if self.connectButton.text() == 'Connect':
            baudrate = int(self.lineEdit.text())
            port = self.comboBox.currentText()
            self.shiva.connect(port, baudrate)
            self.shiva.enableFeedback()
            self.connectButton.setText('Disconnect')
            self.toggleChannelWidgets(True)
        elif self.connectButton.text() == 'Disconnect':
            self.shiva.disableFeedback()
            self.shiva.close()
            self.connectButton.setText('Connect')
            self.resetChannelWidgets()
            self.toggleChannelWidgets(False)

    def onSoundComboBoxSelectionChanged(self, channel):
        try:
            sound = self.noteComboBoxes[channel].currentText()
            if sound:
                print("Channel {}> Sound: {}".format(channel, sound))
                shiva.setSound(channel, sound)
        except (Shiva.ShivaNotConnectedException, SerialException) as e:
            pass

    def onTriggerThresholdSliderReleased(self, channel):
        value = self.triggerThresholdSliders[channel].value()
        print("Channel {}> Trigger: {}".format(channel, value))
        shiva.setThresholds(channel, trigger=value)

    def onOffThresholdSliderReleased(self, channel):
        value = self.offThresholdSliders[channel].value()
        print("Channel {}> Off: {}".format(channel, value))
        shiva.setThresholds(channel, off=value)

    def getSerialPorts(self):
        """
			Returns the available serial ports
		"""
        return glob.glob('/dev/ttyUSB*') + glob.glob('/dev/ttyACM*') + glob.glob("/dev/tty.*") + glob.glob("/dev/cu.*") + glob.glob("/dev/rfcomm*")

    def notify(self, command, channel, value):
        print("Received: {} {} {}".format(command, channel, value))
        if command == 0:
            if not self.enabled_channels[channel]:
                self.enabled_channels[channel] = 1
                self.toggleChannelWidgets(True)
            self.feedback_arrived.emit(channel, value)

if __name__ == '__main__':

    # Create Qt app
    app = QtGui.QApplication(sys.argv)

    # Create a interface to Shiva board
    shiva = Shiva()

    # Create the widget and show it
    gui = ShivaGUI(shiva=shiva)
    gui.show()

    # Run the app
    sys.exit(app.exec_())