# -*- coding: utf-8 -*-

"""
This module initializes the Controller UI with PyQt5
"""

from PyQt5 import QtCore, QtGui, QtWidgets

def add_refresh_button(controllerTab):
    """Add refresh button to controller tab"""
    refreshButton = QtWidgets.QPushButton(controllerTab)
    refreshButton.setGeometry(QtCore.QRect(280, 90, 91, 23))
    refreshButton.setObjectName("refreshButton")
    refreshButton.setText("Refresh")
    return refreshButton
    
# Add to ui_mainwindow.py's setupUi method
def update_controller_tab(controllerTab):
    """Update controller tab with refresh button"""
    return add_refresh_button(controllerTab)