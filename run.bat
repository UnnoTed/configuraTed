set GUI_DIR=.\src\main\python\gui\

pyrcc5 %GUI_DIR%resources.qrc -o %GUI_DIR%resources.py
pyuic5 %GUI_DIR%mainwindow.ui -o %GUI_DIR%mainwindow.py

fbs run
