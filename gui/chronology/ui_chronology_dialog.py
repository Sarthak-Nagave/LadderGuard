# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'chronology_dialog.ui'
##
## Created by: Qt User Interface Compiler version 6.x.x
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
    QFont, QFontDatabase, QGradient, QIcon,
    QImage, QKeySequence, QLinearGradient, QPainter,
    QPalette, QPixmap, QRadialGradient, QTransform)
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QComboBox, QDialog,
    QFormLayout, QGroupBox, QHBoxLayout, QHeaderView,
    QLabel, QLineEdit, QPushButton, QSizePolicy,
    QSpacerItem, QTableWidget, QTableWidgetItem, QVBoxLayout,
    QWidget)

class Ui_ChronologyDialog(object):
    def setupUi(self, ChronologyDialog):
        if not ChronologyDialog.objectName():
            ChronologyDialog.setObjectName(u"ChronologyDialog")
        ChronologyDialog.resize(1000, 700)
        self.verticalLayout = QVBoxLayout(ChronologyDialog)
        self.verticalLayout.setSpacing(12)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.verticalLayout.setContentsMargins(12, 12, 12, 12)
        self.grp_project_info = QGroupBox(ChronologyDialog)
        self.grp_project_info.setObjectName(u"grp_project_info")
        self.formLayoutProjectInfo = QFormLayout(self.grp_project_info)
        self.formLayoutProjectInfo.setObjectName(u"formLayoutProjectInfo")
        self.formLayoutProjectInfo.setHorizontalSpacing(12)
        self.formLayoutProjectInfo.setVerticalSpacing(8)
        self.formLayoutProjectInfo.setContentsMargins(-1, 12, -1, -1)
        self.lbl_project_folder = QLabel(self.grp_project_info)
        self.lbl_project_folder.setObjectName(u"lbl_project_folder")

        self.formLayoutProjectInfo.setWidget(0, QFormLayout.LabelRole, self.lbl_project_folder)

        self.line_project_folder = QLineEdit(self.grp_project_info)
        self.line_project_folder.setObjectName(u"line_project_folder")
        self.line_project_folder.setReadOnly(True)

        self.formLayoutProjectInfo.setWidget(0, QFormLayout.FieldRole, self.line_project_folder)

        self.lbl_excel_template = QLabel(self.grp_project_info)
        self.lbl_excel_template.setObjectName(u"lbl_excel_template")

        self.formLayoutProjectInfo.setWidget(1, QFormLayout.LabelRole, self.lbl_excel_template)

        self.layout_template = QHBoxLayout()
        self.layout_template.setSpacing(6)
        self.layout_template.setObjectName(u"layout_template")
        self.line_excel_template = QLineEdit(self.grp_project_info)
        self.line_excel_template.setObjectName(u"line_excel_template")
        self.line_excel_template.setReadOnly(True)

        self.layout_template.addWidget(self.line_excel_template)

        self.btn_browse_template = QPushButton(self.grp_project_info)
        self.btn_browse_template.setObjectName(u"btn_browse_template")

        self.layout_template.addWidget(self.btn_browse_template)


        self.formLayoutProjectInfo.setLayout(1, QFormLayout.FieldRole, self.layout_template)

        self.lbl_output_file = QLabel(self.grp_project_info)
        self.lbl_output_file.setObjectName(u"lbl_output_file")

        self.formLayoutProjectInfo.setWidget(2, QFormLayout.LabelRole, self.lbl_output_file)

        self.layout_output = QHBoxLayout()
        self.layout_output.setSpacing(6)
        self.layout_output.setObjectName(u"layout_output")
        self.line_output_file = QLineEdit(self.grp_project_info)
        self.line_output_file.setObjectName(u"line_output_file")
        self.line_output_file.setReadOnly(True)

        self.layout_output.addWidget(self.line_output_file)

        self.btn_browse_output = QPushButton(self.grp_project_info)
        self.btn_browse_output.setObjectName(u"btn_browse_output")

        self.layout_output.addWidget(self.btn_browse_output)


        self.formLayoutProjectInfo.setLayout(2, QFormLayout.FieldRole, self.layout_output)


        self.verticalLayout.addWidget(self.grp_project_info)

        self.grp_firmware_entries = QGroupBox(ChronologyDialog)
        self.grp_firmware_entries.setObjectName(u"grp_firmware_entries")
        self.verticalLayoutFirmware = QVBoxLayout(self.grp_firmware_entries)
        self.verticalLayoutFirmware.setObjectName(u"verticalLayoutFirmware")
        self.verticalLayoutFirmware.setContentsMargins(-1, 12, -1, -1)
        self.table_chronology = QTableWidget(self.grp_firmware_entries)
        if (self.table_chronology.columnCount() < 6):
            self.table_chronology.setColumnCount(6)
        __qtablewidgetitem = QTableWidgetItem()
        self.table_chronology.setHorizontalHeaderItem(0, __qtablewidgetitem)
        __qtablewidgetitem1 = QTableWidgetItem()
        self.table_chronology.setHorizontalHeaderItem(1, __qtablewidgetitem1)
        __qtablewidgetitem2 = QTableWidgetItem()
        self.table_chronology.setHorizontalHeaderItem(2, __qtablewidgetitem2)
        __qtablewidgetitem3 = QTableWidgetItem()
        self.table_chronology.setHorizontalHeaderItem(3, __qtablewidgetitem3)
        __qtablewidgetitem4 = QTableWidgetItem()
        self.table_chronology.setHorizontalHeaderItem(4, __qtablewidgetitem4)
        __qtablewidgetitem5 = QTableWidgetItem()
        self.table_chronology.setHorizontalHeaderItem(5, __qtablewidgetitem5)
        self.table_chronology.setObjectName(u"table_chronology")
        self.table_chronology.setAlternatingRowColors(True)
        self.table_chronology.setSelectionBehavior(QAbstractItemView.SelectRows)
        
        header = self.table_chronology.horizontalHeader()
        header.setStretchLastSection(True)

        self.verticalLayoutFirmware.addWidget(self.table_chronology)


        self.verticalLayout.addWidget(self.grp_firmware_entries)

        self.grp_release_info = QGroupBox(ChronologyDialog)
        self.grp_release_info.setObjectName(u"grp_release_info")
        self.formLayoutReleaseInfo = QFormLayout(self.grp_release_info)
        self.formLayoutReleaseInfo.setObjectName(u"formLayoutReleaseInfo")
        self.formLayoutReleaseInfo.setHorizontalSpacing(12)
        self.formLayoutReleaseInfo.setVerticalSpacing(8)
        self.formLayoutReleaseInfo.setContentsMargins(-1, 12, -1, -1)
        self.lbl_released_by = QLabel(self.grp_release_info)
        self.lbl_released_by.setObjectName(u"lbl_released_by")

        self.formLayoutReleaseInfo.setWidget(0, QFormLayout.LabelRole, self.lbl_released_by)

        self.line_released_by = QLineEdit(self.grp_release_info)
        self.line_released_by.setObjectName(u"line_released_by")

        self.formLayoutReleaseInfo.setWidget(0, QFormLayout.FieldRole, self.line_released_by)

        self.lbl_tested_by = QLabel(self.grp_release_info)
        self.lbl_tested_by.setObjectName(u"lbl_tested_by")

        self.formLayoutReleaseInfo.setWidget(1, QFormLayout.LabelRole, self.lbl_tested_by)

        self.line_tested_by = QLineEdit(self.grp_release_info)
        self.line_tested_by.setObjectName(u"line_tested_by")

        self.formLayoutReleaseInfo.setWidget(1, QFormLayout.FieldRole, self.line_tested_by)

        self.lbl_ladder_release = QLabel(self.grp_release_info)
        self.lbl_ladder_release.setObjectName(u"lbl_ladder_release")

        self.formLayoutReleaseInfo.setWidget(2, QFormLayout.LabelRole, self.lbl_ladder_release)

        self.combo_ladder_release = QComboBox(self.grp_release_info)
        self.combo_ladder_release.addItem("")
        self.combo_ladder_release.addItem("")
        self.combo_ladder_release.addItem("")
        self.combo_ladder_release.setObjectName(u"combo_ladder_release")

        self.formLayoutReleaseInfo.setWidget(2, QFormLayout.FieldRole, self.combo_ladder_release)

        self.lbl_operator_mod = QLabel(self.grp_release_info)
        self.lbl_operator_mod.setObjectName(u"lbl_operator_mod")

        self.formLayoutReleaseInfo.setWidget(3, QFormLayout.LabelRole, self.lbl_operator_mod)

        self.combo_operator_modification = QComboBox(self.grp_release_info)
        self.combo_operator_modification.addItem("")
        self.combo_operator_modification.addItem("")
        self.combo_operator_modification.addItem("")
        self.combo_operator_modification.setObjectName(u"combo_operator_modification")

        self.formLayoutReleaseInfo.setWidget(3, QFormLayout.FieldRole, self.combo_operator_modification)

        self.lbl_automation_mod = QLabel(self.grp_release_info)
        self.lbl_automation_mod.setObjectName(u"lbl_automation_mod")

        self.formLayoutReleaseInfo.setWidget(4, QFormLayout.LabelRole, self.lbl_automation_mod)

        self.combo_automation_modification = QComboBox(self.grp_release_info)
        self.combo_automation_modification.addItem("")
        self.combo_automation_modification.addItem("")
        self.combo_automation_modification.addItem("")
        self.combo_automation_modification.setObjectName(u"combo_automation_modification")

        self.formLayoutReleaseInfo.setWidget(4, QFormLayout.FieldRole, self.combo_automation_modification)


        self.verticalLayout.addWidget(self.grp_release_info)

        self.layout_buttons = QHBoxLayout()
        self.layout_buttons.setSpacing(12)
        self.layout_buttons.setObjectName(u"layout_buttons")
        self.layout_buttons.setContentsMargins(-1, 8, -1, -1)
        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)

        self.layout_buttons.addItem(self.horizontalSpacer)

        self.btn_generate = QPushButton(ChronologyDialog)
        self.btn_generate.setObjectName(u"btn_generate")
        self.btn_generate.setMinimumSize(QSize(140, 36))

        self.layout_buttons.addWidget(self.btn_generate)

        self.btn_cancel = QPushButton(ChronologyDialog)
        self.btn_cancel.setObjectName(u"btn_cancel")
        self.btn_cancel.setMinimumSize(QSize(100, 36))

        self.layout_buttons.addWidget(self.btn_cancel)


        self.verticalLayout.addLayout(self.layout_buttons)


        self.retranslateUi(ChronologyDialog)

        QMetaObject.connectSlotsByName(ChronologyDialog)
    # setupUi

    def retranslateUi(self, ChronologyDialog):
        ChronologyDialog.setWindowTitle(QCoreApplication.translate("ChronologyDialog", u"Generate Chronology", None))
        self.grp_project_info.setTitle(QCoreApplication.translate("ChronologyDialog", u"Project Information", None))
        self.lbl_project_folder.setText(QCoreApplication.translate("ChronologyDialog", u"Project Folder:", None))
        self.lbl_excel_template.setText(QCoreApplication.translate("ChronologyDialog", u"Excel Template:", None))
        self.btn_browse_template.setText(QCoreApplication.translate("ChronologyDialog", u"Browse...", None))
        self.lbl_output_file.setText(QCoreApplication.translate("ChronologyDialog", u"Output File:", None))
        self.btn_browse_output.setText(QCoreApplication.translate("ChronologyDialog", u"Browse...", None))
        self.grp_firmware_entries.setTitle(QCoreApplication.translate("ChronologyDialog", u"Detected Firmware Entries", None))
        ___qtablewidgetitem = self.table_chronology.horizontalHeaderItem(0)
        ___qtablewidgetitem.setText(QCoreApplication.translate("ChronologyDialog", u"BIN File", None));
        ___qtablewidgetitem1 = self.table_chronology.horizontalHeaderItem(1)
        ___qtablewidgetitem1.setText(QCoreApplication.translate("ChronologyDialog", u"Version", None));
        ___qtablewidgetitem2 = self.table_chronology.horizontalHeaderItem(2)
        ___qtablewidgetitem2.setText(QCoreApplication.translate("ChronologyDialog", u"PLC Model", None));
        ___qtablewidgetitem3 = self.table_chronology.horizontalHeaderItem(3)
        ___qtablewidgetitem3.setText(QCoreApplication.translate("ChronologyDialog", u"CRC", None));
        ___qtablewidgetitem4 = self.table_chronology.horizontalHeaderItem(4)
        ___qtablewidgetitem4.setText(QCoreApplication.translate("ChronologyDialog", u"Testing Stage", None));
        ___qtablewidgetitem5 = self.table_chronology.horizontalHeaderItem(5)
        ___qtablewidgetitem5.setText(QCoreApplication.translate("ChronologyDialog", u"Reason For Upgrade", None));
        self.grp_release_info.setTitle(QCoreApplication.translate("ChronologyDialog", u"Release Information", None))
        self.lbl_released_by.setText(QCoreApplication.translate("ChronologyDialog", u"Released By:", None))
        self.lbl_tested_by.setText(QCoreApplication.translate("ChronologyDialog", u"Tested By:", None))
        self.lbl_ladder_release.setText(QCoreApplication.translate("ChronologyDialog", u"Ladder Release To Production:", None))
        self.combo_ladder_release.setItemText(0, QCoreApplication.translate("ChronologyDialog", u"Select...", None))
        self.combo_ladder_release.setItemText(1, QCoreApplication.translate("ChronologyDialog", u"Yes", None))
        self.combo_ladder_release.setItemText(2, QCoreApplication.translate("ChronologyDialog", u"No", None))

        self.lbl_operator_mod.setText(QCoreApplication.translate("ChronologyDialog", u"Operator Procedure Modification:", None))
        self.combo_operator_modification.setItemText(0, QCoreApplication.translate("ChronologyDialog", u"Select...", None))
        self.combo_operator_modification.setItemText(1, QCoreApplication.translate("ChronologyDialog", u"Yes", None))
        self.combo_operator_modification.setItemText(2, QCoreApplication.translate("ChronologyDialog", u"No", None))

        self.lbl_automation_mod.setText(QCoreApplication.translate("ChronologyDialog", u"Automation Set Up Modification:", None))
        self.combo_automation_modification.setItemText(0, QCoreApplication.translate("ChronologyDialog", u"Select...", None))
        self.combo_automation_modification.setItemText(1, QCoreApplication.translate("ChronologyDialog", u"Yes", None))
        self.combo_automation_modification.setItemText(2, QCoreApplication.translate("ChronologyDialog", u"No", None))

        self.btn_generate.setText(QCoreApplication.translate("ChronologyDialog", u"Generate Excel", None))
        self.btn_cancel.setText(QCoreApplication.translate("ChronologyDialog", u"Cancel", None))
    # retranslateUi