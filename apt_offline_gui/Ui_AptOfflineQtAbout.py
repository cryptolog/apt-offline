# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'AptOfflineQtAbout.ui'
#
# Created: Sat Nov  6 14:22:12 2010
#      by: PyQt4 UI code generator 4.7.3
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui

class Ui_AboutAptOffline(object):
    def setupUi(self, AboutAptOffline):
        AboutAptOffline.setObjectName("AboutAptOffline")
        AboutAptOffline.setWindowModality(QtCore.Qt.ApplicationModal)
        AboutAptOffline.resize(526, 378)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Fixed, QtGui.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(AboutAptOffline.sizePolicy().hasHeightForWidth())
        AboutAptOffline.setSizePolicy(sizePolicy)
        AboutAptOffline.setMinimumSize(QtCore.QSize(526, 378))
        AboutAptOffline.setMaximumSize(QtCore.QSize(526, 378))
        self.label = QtGui.QLabel(AboutAptOffline)
        self.label.setGeometry(QtCore.QRect(12, 30, 511, 21))
        font = QtGui.QFont()
        font.setPointSize(16)
        self.label.setFont(font)
        self.label.setAlignment(QtCore.Qt.AlignCenter)
        self.label.setObjectName("label")
        self.tabWidget = QtGui.QTabWidget(AboutAptOffline)
        self.tabWidget.setGeometry(QtCore.QRect(7, 90, 510, 241))
        self.tabWidget.setObjectName("tabWidget")
        self.aboutTab = QtGui.QWidget()
        self.aboutTab.setObjectName("aboutTab")
        self.label_3 = QtGui.QLabel(self.aboutTab)
        self.label_3.setGeometry(QtCore.QRect(10, 20, 491, 31))
        self.label_3.setAlignment(QtCore.Qt.AlignLeading|QtCore.Qt.AlignLeft|QtCore.Qt.AlignTop)
        self.label_3.setWordWrap(True)
        self.label_3.setObjectName("label_3")
        self.label_14 = QtGui.QLabel(self.aboutTab)
        self.label_14.setGeometry(QtCore.QRect(10, 46, 481, 61))
        self.label_14.setWordWrap(True)
        self.label_14.setObjectName("label_14")
        self.tabWidget.addTab(self.aboutTab, "")
        self.authorTab = QtGui.QWidget()
        self.authorTab.setObjectName("authorTab")
        self.label_4 = QtGui.QLabel(self.authorTab)
        self.label_4.setGeometry(QtCore.QRect(10, 10, 111, 16))
        self.label_4.setObjectName("label_4")
        self.label_5 = QtGui.QLabel(self.authorTab)
        self.label_5.setGeometry(QtCore.QRect(30, 30, 271, 16))
        self.label_5.setObjectName("label_5")
        self.label_6 = QtGui.QLabel(self.authorTab)
        self.label_6.setGeometry(QtCore.QRect(10, 60, 131, 16))
        self.label_6.setObjectName("label_6")
        self.label_7 = QtGui.QLabel(self.authorTab)
        self.label_7.setGeometry(QtCore.QRect(30, 80, 261, 16))
        self.label_7.setObjectName("label_7")
        self.label_8 = QtGui.QLabel(self.authorTab)
        self.label_8.setGeometry(QtCore.QRect(30, 100, 271, 16))
        self.label_8.setObjectName("label_8")
        self.tabWidget.addTab(self.authorTab, "")
        self.thanksTab = QtGui.QWidget()
        self.thanksTab.setObjectName("thanksTab")
        self.label_9 = QtGui.QLabel(self.thanksTab)
        self.label_9.setGeometry(QtCore.QRect(10, 10, 221, 16))
        self.label_9.setObjectName("label_9")
        self.label_10 = QtGui.QLabel(self.thanksTab)
        self.label_10.setGeometry(QtCore.QRect(10, 30, 141, 16))
        self.label_10.setObjectName("label_10")
        self.label_11 = QtGui.QLabel(self.thanksTab)
        self.label_11.setGeometry(QtCore.QRect(10, 50, 161, 16))
        self.label_11.setObjectName("label_11")
        self.label_12 = QtGui.QLabel(self.thanksTab)
        self.label_12.setGeometry(QtCore.QRect(10, 70, 161, 16))
        self.label_12.setObjectName("label_12")
        self.label_13 = QtGui.QLabel(self.thanksTab)
        self.label_13.setGeometry(QtCore.QRect(10, 110, 301, 31))
        self.label_13.setWordWrap(True)
        self.label_13.setObjectName("label_13")
        self.tabWidget.addTab(self.thanksTab, "")
        self.licenseTab = QtGui.QWidget()
        self.licenseTab.setObjectName("licenseTab")
        self.licenseText = QtGui.QPlainTextEdit(self.licenseTab)
        self.licenseText.setGeometry(QtCore.QRect(4, 4, 490, 203))
        font = QtGui.QFont()
        font.setPointSize(8)
        self.licenseText.setFont(font)
        self.licenseText.setObjectName("licenseText")
        self.tabWidget.addTab(self.licenseTab, "")
        self.label_2 = QtGui.QLabel(AboutAptOffline)
        self.label_2.setGeometry(QtCore.QRect(10, 60, 511, 16))
        self.label_2.setAlignment(QtCore.Qt.AlignCenter)
        self.label_2.setObjectName("label_2")
        self.pushButton = QtGui.QPushButton(AboutAptOffline)
        self.pushButton.setGeometry(QtCore.QRect(416, 340, 101, 31))
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap(":/icons/icons/dialog-cancel.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.pushButton.setIcon(icon)
        self.pushButton.setObjectName("pushButton")

        self.retranslateUi(AboutAptOffline)
        self.tabWidget.setCurrentIndex(3)
        QtCore.QObject.connect(self.pushButton, QtCore.SIGNAL("clicked()"), AboutAptOffline.close)
        QtCore.QMetaObject.connectSlotsByName(AboutAptOffline)

    def retranslateUi(self, AboutAptOffline):
        AboutAptOffline.setWindowTitle(QtGui.QApplication.translate("AboutAptOffline", "About Apt-Offline", None, QtGui.QApplication.UnicodeUTF8))
        self.label.setText(QtGui.QApplication.translate("AboutAptOffline", "Apt-Offline", None, QtGui.QApplication.UnicodeUTF8))
        self.label_3.setText(QtGui.QApplication.translate("AboutAptOffline", "apt-offline is an Offline APT Package Manager for Debian and derivatives. ", None, QtGui.QApplication.UnicodeUTF8))
        self.label_14.setText(QtGui.QApplication.translate("AboutAptOffline", "apt-offline can fully update/upgrade your disconnected Debian box without the need of connecting it to the network.  \n"
"\n"
"This is a Graphical User Interface which exposes the functionality of apt-offline.", None, QtGui.QApplication.UnicodeUTF8))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.aboutTab), QtGui.QApplication.translate("AboutAptOffline", "About", None, QtGui.QApplication.UnicodeUTF8))
        self.label_4.setText(QtGui.QApplication.translate("AboutAptOffline", "Written by:", None, QtGui.QApplication.UnicodeUTF8))
        self.label_5.setText(QtGui.QApplication.translate("AboutAptOffline", "Ritesh Raj Sarraf <rrs@researchut.com>", None, QtGui.QApplication.UnicodeUTF8))
        self.label_6.setText(QtGui.QApplication.translate("AboutAptOffline", "GUI written by:", None, QtGui.QApplication.UnicodeUTF8))
        self.label_7.setText(QtGui.QApplication.translate("AboutAptOffline", "Manish Sinha <mail@manishsinha.net>", None, QtGui.QApplication.UnicodeUTF8))
        self.label_8.setText(QtGui.QApplication.translate("AboutAptOffline", "Abhishek Mishra <ideamonk@gmail.com>", None, QtGui.QApplication.UnicodeUTF8))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.authorTab), QtGui.QApplication.translate("AboutAptOffline", "Author", None, QtGui.QApplication.UnicodeUTF8))
        self.label_9.setText(QtGui.QApplication.translate("AboutAptOffline", "Peter Otten", None, QtGui.QApplication.UnicodeUTF8))
        self.label_10.setText(QtGui.QApplication.translate("AboutAptOffline", "Duncan Booth", None, QtGui.QApplication.UnicodeUTF8))
        self.label_11.setText(QtGui.QApplication.translate("AboutAptOffline", "Simon Forman", None, QtGui.QApplication.UnicodeUTF8))
        self.label_12.setText(QtGui.QApplication.translate("AboutAptOffline", "Dennis Lee Bieber", None, QtGui.QApplication.UnicodeUTF8))
        self.label_13.setText(QtGui.QApplication.translate("AboutAptOffline", "The awesome Directi people for their office space required for the mini hackfests", None, QtGui.QApplication.UnicodeUTF8))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.thanksTab), QtGui.QApplication.translate("AboutAptOffline", "Thanks To", None, QtGui.QApplication.UnicodeUTF8))
        self.licenseText.setPlainText(QtGui.QApplication.translate("AboutAptOffline", "LICENSE not found. Please contact the developers immediately.", None, QtGui.QApplication.UnicodeUTF8))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.licenseTab), QtGui.QApplication.translate("AboutAptOffline", "License", None, QtGui.QApplication.UnicodeUTF8))
        self.label_2.setText(QtGui.QApplication.translate("AboutAptOffline", "A GUI for apt-offline - an offline APT Package Manager", None, QtGui.QApplication.UnicodeUTF8))
        self.pushButton.setText(QtGui.QApplication.translate("AboutAptOffline", "Close", None, QtGui.QApplication.UnicodeUTF8))

import resources_rc
