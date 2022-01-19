# -*- coding: utf-8 -*-
######################################################################################################################
# Copyright (C) 2017-2021 Spine project consortium
# This file is part of Spine Items.
# Spine Items is free software: you can redistribute it and/or modify it under the terms of the GNU Lesser General
# Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option)
# any later version. This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
# without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Lesser General
# Public License for more details. You should have received a copy of the GNU Lesser General Public License along with
# this program. If not, see <http://www.gnu.org/licenses/>.
######################################################################################################################

################################################################################
## Form generated from reading UI file 'data_connection_properties.ui'
##
## Created by: Qt User Interface Compiler version 5.14.2
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide2.QtCore import (QCoreApplication, QDate, QDateTime, QMetaObject,
    QObject, QPoint, QRect, QSize, QTime, QUrl, Qt)
from PySide2.QtGui import (QBrush, QColor, QConicalGradient, QCursor, QFont,
    QFontDatabase, QIcon, QKeySequence, QLinearGradient, QPalette, QPainter,
    QPixmap, QRadialGradient)
from PySide2.QtWidgets import *

from spine_items.widgets import ReferencesTreeView
from spine_items.widgets import DataTreeView

from spine_items import resources_icons_rc

class Ui_Form(object):
    def setupUi(self, Form):
        if not Form.objectName():
            Form.setObjectName(u"Form")
        Form.resize(276, 476)
        self.verticalLayout = QVBoxLayout(Form)
        self.verticalLayout.setSpacing(0)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.scrollArea_2 = QScrollArea(Form)
        self.scrollArea_2.setObjectName(u"scrollArea_2")
        self.scrollArea_2.setWidgetResizable(True)
        self.scrollAreaWidgetContents_2 = QWidget()
        self.scrollAreaWidgetContents_2.setObjectName(u"scrollAreaWidgetContents_2")
        self.scrollAreaWidgetContents_2.setGeometry(QRect(0, 0, 274, 474))
        self.verticalLayout_16 = QVBoxLayout(self.scrollAreaWidgetContents_2)
        self.verticalLayout_16.setObjectName(u"verticalLayout_16")
        self.treeView_dc_references = ReferencesTreeView(self.scrollAreaWidgetContents_2)
        self.treeView_dc_references.setObjectName(u"treeView_dc_references")
        sizePolicy = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.treeView_dc_references.sizePolicy().hasHeightForWidth())
        self.treeView_dc_references.setSizePolicy(sizePolicy)
        font = QFont()
        font.setPointSize(9)
        self.treeView_dc_references.setFont(font)
        self.treeView_dc_references.setContextMenuPolicy(Qt.CustomContextMenu)
        self.treeView_dc_references.setAcceptDrops(True)
        self.treeView_dc_references.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.treeView_dc_references.setTextElideMode(Qt.ElideLeft)
        self.treeView_dc_references.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.treeView_dc_references.setIndentation(5)
        self.treeView_dc_references.setUniformRowHeights(True)
        self.treeView_dc_references.header().setStretchLastSection(True)

        self.verticalLayout_16.addWidget(self.treeView_dc_references)

        self.horizontalLayout_2 = QHBoxLayout()
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.toolButton_plus = QToolButton(self.scrollAreaWidgetContents_2)
        self.toolButton_plus.setObjectName(u"toolButton_plus")
        sizePolicy1 = QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.toolButton_plus.sizePolicy().hasHeightForWidth())
        self.toolButton_plus.setSizePolicy(sizePolicy1)
        self.toolButton_plus.setMinimumSize(QSize(22, 22))
        self.toolButton_plus.setMaximumSize(QSize(22, 22))
        font1 = QFont()
        font1.setPointSize(10)
        font1.setBold(True)
        font1.setWeight(75)
        self.toolButton_plus.setFont(font1)
        icon = QIcon()
        icon.addFile(u":/icons/plus.svg", QSize(), QIcon.Normal, QIcon.Off)
        self.toolButton_plus.setIcon(icon)
        self.toolButton_plus.setPopupMode(QToolButton.InstantPopup)

        self.horizontalLayout_2.addWidget(self.toolButton_plus)

        self.toolButton_minus = QToolButton(self.scrollAreaWidgetContents_2)
        self.toolButton_minus.setObjectName(u"toolButton_minus")
        sizePolicy1.setHeightForWidth(self.toolButton_minus.sizePolicy().hasHeightForWidth())
        self.toolButton_minus.setSizePolicy(sizePolicy1)
        self.toolButton_minus.setMinimumSize(QSize(22, 22))
        self.toolButton_minus.setMaximumSize(QSize(22, 22))
        self.toolButton_minus.setFont(font1)
        icon1 = QIcon()
        icon1.addFile(u":/icons/minus.svg", QSize(), QIcon.Normal, QIcon.Off)
        self.toolButton_minus.setIcon(icon1)
        self.toolButton_minus.setPopupMode(QToolButton.InstantPopup)

        self.horizontalLayout_2.addWidget(self.toolButton_minus)

        self.toolButton_add = QToolButton(self.scrollAreaWidgetContents_2)
        self.toolButton_add.setObjectName(u"toolButton_add")
        self.toolButton_add.setMinimumSize(QSize(22, 22))
        self.toolButton_add.setMaximumSize(QSize(22, 22))
        icon2 = QIcon()
        icon2.addFile(u":/icons/file-download.svg", QSize(), QIcon.Normal, QIcon.Off)
        self.toolButton_add.setIcon(icon2)
        self.toolButton_add.setIconSize(QSize(16, 16))
        self.toolButton_add.setPopupMode(QToolButton.InstantPopup)

        self.horizontalLayout_2.addWidget(self.toolButton_add)

        self.horizontalSpacer_2 = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)

        self.horizontalLayout_2.addItem(self.horizontalSpacer_2)


        self.verticalLayout_16.addLayout(self.horizontalLayout_2)

        self.treeView_dc_data = DataTreeView(self.scrollAreaWidgetContents_2)
        self.treeView_dc_data.setObjectName(u"treeView_dc_data")
        sizePolicy.setHeightForWidth(self.treeView_dc_data.sizePolicy().hasHeightForWidth())
        self.treeView_dc_data.setSizePolicy(sizePolicy)
        self.treeView_dc_data.setFont(font)
        self.treeView_dc_data.setContextMenuPolicy(Qt.CustomContextMenu)
        self.treeView_dc_data.setAcceptDrops(True)
        self.treeView_dc_data.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.treeView_dc_data.setTextElideMode(Qt.ElideLeft)
        self.treeView_dc_data.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.treeView_dc_data.setIndentation(5)
        self.treeView_dc_data.setUniformRowHeights(True)
        self.treeView_dc_data.header().setStretchLastSection(True)

        self.verticalLayout_16.addWidget(self.treeView_dc_data)

        self.line_3 = QFrame(self.scrollAreaWidgetContents_2)
        self.line_3.setObjectName(u"line_3")
        self.line_3.setFrameShape(QFrame.HLine)
        self.line_3.setFrameShadow(QFrame.Sunken)

        self.verticalLayout_16.addWidget(self.line_3)

        self.horizontalLayout_7 = QHBoxLayout()
        self.horizontalLayout_7.setObjectName(u"horizontalLayout_7")
        self.horizontalSpacer_10 = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)

        self.horizontalLayout_7.addItem(self.horizontalSpacer_10)

        self.toolButton_dc_open_dir = QToolButton(self.scrollAreaWidgetContents_2)
        self.toolButton_dc_open_dir.setObjectName(u"toolButton_dc_open_dir")
        sizePolicy1.setHeightForWidth(self.toolButton_dc_open_dir.sizePolicy().hasHeightForWidth())
        self.toolButton_dc_open_dir.setSizePolicy(sizePolicy1)
        self.toolButton_dc_open_dir.setMinimumSize(QSize(22, 22))
        self.toolButton_dc_open_dir.setMaximumSize(QSize(22, 22))
        icon3 = QIcon()
        icon3.addFile(u":/icons/folder-open-regular.svg", QSize(), QIcon.Normal, QIcon.Off)
        self.toolButton_dc_open_dir.setIcon(icon3)

        self.horizontalLayout_7.addWidget(self.toolButton_dc_open_dir)


        self.verticalLayout_16.addLayout(self.horizontalLayout_7)

        self.scrollArea_2.setWidget(self.scrollAreaWidgetContents_2)

        self.verticalLayout.addWidget(self.scrollArea_2)


        self.retranslateUi(Form)

        QMetaObject.connectSlotsByName(Form)
    # setupUi

    def retranslateUi(self, Form):
        Form.setWindowTitle(QCoreApplication.translate("Form", u"Form", None))
#if QT_CONFIG(tooltip)
        self.treeView_dc_references.setToolTip(QCoreApplication.translate("Form", u"<html><head/><body><p>Drag-and-drop files here, they will be added as references.</p></body></html>", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(tooltip)
        self.toolButton_plus.setToolTip(QCoreApplication.translate("Form", u"<html><head/><body><p>Add references</p></body></html>", None))
#endif // QT_CONFIG(tooltip)
        self.toolButton_plus.setText("")
#if QT_CONFIG(tooltip)
        self.toolButton_minus.setToolTip(QCoreApplication.translate("Form", u"<html><head/><body><p>Remove selected references or all if nothing is selected</p></body></html>", None))
#endif // QT_CONFIG(tooltip)
        self.toolButton_minus.setText("")
#if QT_CONFIG(tooltip)
        self.toolButton_add.setToolTip(QCoreApplication.translate("Form", u"<html><head/><body><p>Add references to project. Copies files to Data connection's directory.</p></body></html>", None))
#endif // QT_CONFIG(tooltip)
        self.toolButton_add.setText("")
#if QT_CONFIG(tooltip)
        self.treeView_dc_data.setToolTip(QCoreApplication.translate("Form", u"<html><head/><body><p>Drag-and-drop files here, they will be copied to the data directory.</p></body></html>", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(tooltip)
        self.toolButton_dc_open_dir.setToolTip(QCoreApplication.translate("Form", u"<html><head/><body><p>Open this Data Connection's project directory in file browser</p></body></html>", None))
#endif // QT_CONFIG(tooltip)
    # retranslateUi

