from fbs_runtime.application_context import ApplicationContext
from PyQt5.QtWidgets import (QMainWindow, QMessageBox)
from PyQt5.QtCore import (QThread, pyqtSignal)
from PyQt5.QtGui import (QIcon)
from decimal import Decimal, ROUND_FLOOR
from logger import log
from pprint import pprint
from steam import steam
from math import ceil, floor
from gui import (mainwindow, resources)

import urllib.request
import qdarkstyle
import subprocess
import webbrowser
import speedtest
import win32api
import ctypes
import psutil
import xerox
import time
import yaml
import sys
import os

VERSION = "1.0.0"

launchOptions = [
    "-novid", "-nojoy", "-nosteamcontroller", "-softparticlesdefaultoff",
    "-reuse", "-nohltv"
]

dxlevels = ["80", "81", "90", "92", "95 (default)", "98"]


def is_admin():
  try:
    return ctypes.windll.shell32.IsUserAnAdmin()
  except:
    return False


class SpeedTest(QThread):
  signal = pyqtSignal("PyQt_PyObject")

  def __init__(self):
    QThread.__init__(self)

  def run(self):
    s = speedtest.Speedtest()
    s.get_best_server()
    s.download()
    s.upload()
    s.results.share()

    results_dict = s.results.dict()
    # results_dict = {"download": 0, "upload": 0}
    log.debug(results_dict)
    self.signal.emit(results_dict)


class App(QMainWindow):

  def __init__(self, parent=None):
    super(App, self).__init__(parent)
    self.ui = mainwindow.Ui_MainWindow()
    self.ui.setupUi(self)
    self.setWindowTitle("configuraTed v{v}".format(v=VERSION))
    self.ui.nextButton.clicked.connect(self.onNextClick)
    self.ui.prevButton.clicked.connect(self.onPrevClick)
    self.ui.autoRefreshRate.clicked.connect(self.getRefreshRate)
    self.ui.copyBackupPath.clicked.connect(self.copyBackupPath)
    self.ui.copyConfiguratedPath.clicked.connect(self.copyConfiguratedPath)
    self.ui.toggleRefreshRate.stateChanged.connect(self.onToggleRefreshRate)
    self.ui.refreshConnectionSpeed.clicked.connect(self.getConnectionSpeed)
    self.ui.refreshConnectionSpeed.setIcon(QIcon(":/icons/icons/refresh.png"))
    self.toggleButton(self.ui.nextButton, "show")
    self.toggleButton(self.ui.prevButton, "hide")
    self.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())

    self.custom = ""
    self.configs = {}
    self.backupPath = ""
    log.debug("loading configs.yml")
    try:
      with open("configs.yml", encoding="utf8") as f:
        self.configs = yaml.safe_load(f)
    except Exception as e:
      msg = "Error while trying to get configs.yml: %s" % e
      log.error(msg, exc_info=True)
      QMessageBox.critical(self, "Error", msg)
    log.debug("configs.yml loaded")

    self.ui.configList.addItem("TF2's Default")

    for id, cfg in self.configs["list"].items():
      log.debug("%s = %s" % (id, cfg))
      self.ui.configList.addItem(cfg["name"])

    self.ui.configList.setCurrentIndex(5)

    for dxl in dxlevels:
      self.ui.dxlevelList.addItem(dxl)

    self.ui.connectionType.addItem("Cable")
    self.ui.connectionType.addItem("Wifi")
    self.ui.connectionType.addItem("Mobile")

    self.ui.dxlevelList.setCurrentIndex(4)
    self.ui.pages.setCurrentIndex(0)
    self.shouldTestConnection = True
    self.getRefreshRate()

  def openBackupPath(self):
    subprocess.Popen("explorer /select, \"%s\"" % self.backupPath)

  def openConfiguratedPath(self):
    subprocess.Popen("explorer /select, \"%s\"" % self.configuratedPath)

  def copyBackupPath(self):
    xerox.copy(self.backupPath)

  def copyConfiguratedPath(self):
    xerox.copy(self.configuratedPath)

  def getRefreshRate(self):
    log.debug("getting refresh rate...")
    try:
      displayfrequency = getattr(
          win32api.EnumDisplaySettings(win32api.EnumDisplayDevices().DeviceName,
                                       -1), 'DisplayFrequency')
      self.ui.refreshRate.setText(str(displayfrequency))
      log.debug("refresh rate: %s" % displayfrequency)
    except Exception as e:
      msg = "Error while trying to get the refresh rate: %s" % e
      log.error(msg, exc_info=True)
      QMessageBox.critical(self, "Error", msg)

  def onToggleRefreshRate(self):
    self.ui.refreshRate.setDisabled(self.ui.toggleRefreshRate.isChecked())

  def clamp(self, actual, mi, ma):
    return max(min(actual, ma), mi)

  def onSpeedTestDone(self, data):
    self.shouldTestConnection = False
    self.ui.statusbar.showMessage("Done, click next to continue.")
    log.debug("done: %s" % data)
    self.toggleButton(self.ui.nextButton, "show")
    self.ui.refreshConnectionSpeed.setEnabled(True)

    d = str(data["download"] / 1000000)
    d = d[0:d.index(".") + 2]

    u = str(data["upload"] / 1000000)
    u = u[0:u.index(".") + 2]
    self.ui.connectionSpeed.setText("{down} Down / {up} Up (Mbps)".format(
        down=d, up=u))

    speed = min(float(d), float(u))

    # rate
    rate = float(speed * 125000)
    rate = self.clamp(rate, 40000, 324192)
    self.custom_net = "\nrate " + str(rate)

    # net split
    net_split = float(speed * 125000)
    net_split = self.clamp(net_split, 3500, 324192)
    self.custom_net += "\nnet_splitpacket_maxrate " + str(net_split)

    # net clear
    self.custom_net += "\nnet_maxcleartime " + str(
        max(4000 / 786432, 4000 / (float(u) * 125000)))
    log.debug(self.custom_net)

  def toggleButton(self, btn, state):
    if state == "hide":
      btn.setStyleSheet(
          "background-color: rgba(0, 0, 0, 0); color: rgba(0, 0, 0, 0);")
      btn.setEnabled(False)
    else:
      btn.setStyleSheet("")
      btn.setEnabled(True)

  def getConnectionSpeed(self):
    try:
      self.st = SpeedTest()
      self.st.signal.connect(self.onSpeedTestDone)
      self.st.start()
      self.ui.statusbar.showMessage("Testing connection speed...")
      self.toggleButton(self.ui.nextButton, "hide")
      self.ui.refreshConnectionSpeed.setEnabled(False)
    except:
      e = sys.exc_info()[0]
      log.error("Error while trying to get the connection speed: %s" % e)
      QMessageBox.critical(self, "Error", "%s" % e)

  def onNextClick(self):
    log.debug("next")
    c = self.ui.pages.currentIndex()
    if c == 0 and self.shouldTestConnection:
      self.getConnectionSpeed()
      return
    elif c == 3:
      self.Install()

    self.ui.pages.setCurrentIndex(c + 1)
    self.toggleButton(self.ui.prevButton, "show")

    if (c + 1) == 3:
      self.ui.nextButton.setText("Install")
    else:
      self.ui.nextButton.setText("Next")

  def onPrevClick(self):
    log.debug("prev")
    c = self.ui.pages.currentIndex()
    if c > 0:
      self.ui.pages.setCurrentIndex(c - 1)
      if c - 1 == 0:
        self.ui.prevButton.setEnabled(False)

      self.ui.nextButton.setText("Next")

  def Install(self):
    log.debug("install")
    self.toggleButton(self.ui.prevButton, "hide")
    self.toggleButton(self.ui.nextButton, "hide")

    buttonReply = QMessageBox.question(
        self, "Confirmation", "Do you wanna proceed with the installation?",
        QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
    if buttonReply == QMessageBox.No:
      return

    self.ui.statusbar.showMessage("Installing...")
    shouldReset = self.ui.resetBox.isChecked()
    shouldLaunch = self.ui.launchBox.isChecked()
    dxlevel = self.ui.dxlevelList.currentText()
    cfg = self.ui.configList.currentText()

    try:
      if shouldReset:
        self.ui.statusbar.showMessage("Reset TF2: finding steam's path...")
        self.errorMessage = "steam.findGame()"
        steam.findGame()

        self.ui.statusbar.showMessage("Reset TF2: backing up user's config...")
        self.errorMessage = "steam.backupUserConfig()"
        self.backupPath = steam.backupUserConfig()

        self.ui.statusbar.showMessage(
            "Reset TF2: disabling steam's cloud for tf2...")
        self.errorMessage = "steam.disableCloud()"
        steam.disableCloud()

        self.ui.statusbar.showMessage("Reset TF2: validating tf2's files...")
        self.errorMessage = "steam.validateGameFiles()"
        steam.validateGameFiles()

        self.ui.statusbar.showMessage(
            "Reset TF2: generating tf2's default config...")
        self.errorMessage = "steam.autoConfig()"
        steam.autoConfig()

        time.sleep(4)

      if shouldLaunch or dxlevel[0:2] != "95":
        self.ui.statusbar.showMessage(
            "Setting tf2's dxlevel to {dxlevel}...".format(dxlevel=dxlevel))
        self.errorMessage = "steam.autoConfig set_dxlevel"
        steam.autoConfig(mode="set_dxlevel", dxlevel=dxlevel[0:2])

        self.ui.statusbar.showMessage(
            "Setting tf2's launch options".format(dxlevel=dxlevel))
        launchOptions.append("-freq " + self.ui.refreshRate.text())
        self.errorMessage = "steam.setLaunchOptions()"
        steam.setLaunchOptions(launchOptions)

      self.ui.statusbar.showMessage("Installing config: {cfg}".format(cfg=cfg))
      self.errorMessage = "installConfig()"
      self.installConfig()

      self.ui.backupPath.setText(self.backupPath)
      self.ui.statusbar.showMessage("Done, you can play tf2 now.")
      self.ui.pages.setCurrentIndex(self.ui.pages.currentIndex() + 1)
    except Exception as e:
      msg = "%s: %s" % (self.errorMessage, e)
      log.error(msg, exc_info=True)
      QMessageBox.critical(self, "Error", msg)

  def installConfig(self):
    log.debug("installing config")
    current = self.ui.configList.currentText()
    if current == "TF2's Default":
      self.configuratedPath = steam.findGame() + "cfg\\"
      return

    cfg = {}
    for _id, c in self.configs["list"].items():
      if c["name"] == current:
        cfg = c
        break

    customPath = steam.findGame() + "custom\\"
    self.configuratedPath = customPath + "configurated\\"

    log.debug("downloading cfg")
    ndir = self.configuratedPath + "cfg\\"
    log.debug("making dirs: %s" % ndir)
    os.makedirs(ndir, exist_ok=True)

    # when type is autoexec it downloads directly to: tf/custom/configurated/
    if cfg["type"] == "autoexec":
      urllib.request.urlretrieve(cfg["url"] + cfg["file"], ndir + cfg["file"])
    else:
      urllib.request.urlretrieve(cfg["url"] + cfg["file"],
                                 customPath + cfg["file"])

    customPath = self.configuratedPath
    self.ui.configuratedPath.setText(customPath)

    if "mastercomfig" in cfg["name"].lower():
      log.debug(
          "cfg is mastercomfig, creating cfg's custom files at tf/custom/configurated/cfg"
      )
      files = [
          "custom", "scout", "soldier", "demoman", "engineer", "heavyweapons",
          "medic", "pyro", "sniper", "spy", "game_overrides", "listenserver"
      ]

      if not ("experimental" in cfg["name"].lower()):
        log.debug("adding _c to cfg file names")
        for i in range(len(files)):
          if files[i] != "custom":
            files[i] = files[i] + "_c"

      for name in files:
        open(customPath + "cfg\\" + name + ".cfg", "w", encoding="utf8").close()

      f = open(customPath + "cfg\\" + "custom.cfg", "w", encoding="utf8")
      f.write(self.custom + self.custom_net)
      f.close()


if __name__ == "__main__":
  appctxt = ApplicationContext()  # 1. Instantiate ApplicationContext
  window = App()
  window.show()
  exit_code = appctxt.app.exec_()  # 2. Invoke appctxt.app.exec_()
  sys.exit(exit_code)
