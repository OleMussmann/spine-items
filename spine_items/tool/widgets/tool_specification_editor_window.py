######################################################################################################################
# Copyright (C) 2017-2022 Spine project consortium
# This file is part of Spine Items.
# Spine Items is free software: you can redistribute it and/or modify it under the terms of the GNU Lesser General
# Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option)
# any later version. This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
# without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Lesser General
# Public License for more details. You should have received a copy of the GNU Lesser General Public License along with
# this program. If not, see <http://www.gnu.org/licenses/>.
######################################################################################################################

"""
QWidget that is used to create or edit Tool specifications.
In the former case it is presented empty, but in the latter it
is filled with all the information from the specification being edited.

:author: M. Marin (KTH), P. Savolainen (VTT)
:date:   12.4.2018
"""
import logging
import os
from copy import deepcopy
from operator import methodcaller
from PySide6.QtGui import QStandardItemModel, QStandardItem, QTextDocument, QFont
from PySide6.QtWidgets import QInputDialog, QFileDialog, QFileIconProvider, QMessageBox, QLabel
from PySide6.QtCore import Slot, Qt, QFileInfo, QTimer, QItemSelection, QModelIndex, QItemSelectionModel
from spinetoolbox.helpers import busy_effect, open_url, same_path
from spinetoolbox.widgets.custom_qwidgets import ToolBarWidget
from spinetoolbox.config import STATUSBAR_SS
from spinetoolbox.project_item.specification_editor_window import (
    SpecificationEditorWindowBase,
    ChangeSpecPropertyCommand,
)
from spine_engine.utils.command_line_arguments import split_cmdline_args
from spine_items.tool.widgets.tool_spec_optional_widgets import (
    PythonToolSpecOptionalWidget,
    ExecutableToolSpecOptionalWidget,
)
from ..item_info import ItemInfo
from ..tool_specifications import TOOL_TYPES, make_specification


class ToolSpecificationEditorWindow(SpecificationEditorWindowBase):
    """A widget to query user's preferences for a new tool specification."""

    def __init__(self, toolbox, specification=None, item=None):
        """
        Args:
            toolbox (ToolboxUI): QMainWindow instance
            specification (ToolSpecification, optional): If given, the form is pre-filled with this specification
            item (ProjectItem, optional): Sets the spec for this item if accepted
        """
        super().__init__(toolbox, specification, item)  # Inherit stylesheet from ToolboxUI
        self._project = self._toolbox.project()
        # Customize text edit main program
        self._ui.textEdit_program.setEnabled(False)
        self._programfile_documents = {}
        self._programfile_set_dirty_slots = {}
        # Setup statusbar
        self._label_main_path = QLabel()
        label = QLabel("Source dir:")
        font = QFont()
        font.setPointSize(10)
        label.setFont(font)
        font = QFont(font)
        font.setBold(True)
        self._label_main_path.setFont(font)
        self._ui.statusbar.addPermanentWidget(label)
        self._ui.statusbar.addPermanentWidget(self._label_main_path)
        self._ui.statusbar.setStyleSheet(STATUSBAR_SS)
        # init models
        self.programfiles_model = QStandardItemModel(self)
        self.io_files_model = QStandardItemModel(self)
        # init ui
        self._ui.treeView_programfiles.setModel(self.programfiles_model)
        self._ui.treeView_io_files.setModel(self.io_files_model)
        self._ui.comboBox_tooltype.addItems(TOOL_TYPES)
        self._ui.comboBox_tooltype.setCurrentIndex(-1)
        # if a specification is given, fill the form with data from it
        if specification is not None:
            self._ui.lineEdit_args.setText(" ".join(specification.cmdline_args))
            tooltype = specification.tooltype.lower()
            index = next(iter(k for k, t in enumerate(TOOL_TYPES) if t.lower() == tooltype), -1)
            self._ui.comboBox_tooltype.setCurrentIndex(index)
            self._ui.textEdit_program.set_lexer_name(tooltype.lower())
            self._show_optional_widget(index)
            specification.set_execution_settings()  # Set default execution settings
            self._init_optional_widget(specification)
        # Init lists
        programfiles = list(specification.includes) if specification else []
        # Get first item from programfiles list as the main program file
        main_program_file = programfiles.pop(0) if programfiles else None
        inputfiles = list(specification.inputfiles) if specification else []
        inputfiles_opt = list(specification.inputfiles_opt) if specification else []
        outputfiles = list(specification.outputfiles) if specification else []
        self.includes_main_path = specification.path if specification else None
        self.spec_dict = deepcopy(specification.to_dict()) if specification else dict(item_type=ItemInfo.item_type())
        # Populate lists (this will also create headers)
        self.init_programfile_list()
        self.init_io_file_list()
        self.populate_programfile_list(programfiles)
        self.populate_inputfiles_list(inputfiles)
        self.populate_inputfiles_opt_list(inputfiles_opt)
        self.populate_outputfiles_list(outputfiles)
        if main_program_file:
            self._set_main_program_file(os.path.join(self.includes_main_path, main_program_file))
        else:
            self._label_main_path.setText(self.includes_main_path)
        self.connect_signals()
        # Select main program file index
        parent = self.programfiles_model.index(0, 0)
        index = self.programfiles_model.index(0, 0, parent)
        selection_model = self._ui.treeView_programfiles.selectionModel()
        selection_model.setCurrentIndex(index, QItemSelectionModel.Select)

    def _make_ui(self):
        from ..ui.tool_specification_form import Ui_MainWindow  # pylint: disable=import-outside-toplevel

        return Ui_MainWindow()

    @property
    def qsettings(self):
        return self._app_settings

    @property
    def settings_group(self):
        return "toolSpecificationEditorWindow"

    def _restore_dock_widgets(self):
        docks = (self._ui.dockWidget_program_files, self._ui.dockWidget_program)
        self.splitDockWidget(*docks, Qt.Orientation.Horizontal)
        width = sum(d.width() for d in docks)
        self.resizeDocks(docks, [width * x for x in (0.3, 0.7)], Qt.Orientation.Horizontal)
        docks = (self._ui.dockWidget_program_files, self._ui.dockWidget_io_files)
        self.splitDockWidget(*docks, Qt.Orientation.Vertical)
        height = sum(d.height() for d in docks)
        self.resizeDocks(docks, [height * x for x in (0.6, 0.4)], Qt.Orientation.Vertical)

    @Slot(bool)
    def _update_window_modified(self, _clean):
        clean = self._undo_stack.isClean() and not any(doc.isModified() for doc in self._programfile_documents.values())
        super()._update_window_modified(clean)

    def _make_optional_widget(self, toolspectype):
        """Returns an optional widget based on tool spec type.
        Embedded to the main window in ``self._show_optional_widget()``.

        Args:
            toolspectype (str): Tool spec type

        Returns:
            ToolSpecOptionalWidget
        """
        # For Python Tool specs, return the jupyter kernel spec selector
        if toolspectype.lower() == "python":
            return PythonToolSpecOptionalWidget(self)
        if toolspectype.lower() == "executable":
            return ExecutableToolSpecOptionalWidget(self)
        return None

    def _get_optional_widget(self, toolspectype):
        """Returns the current optional widget for given tool spec type or None if unavailable."""
        if toolspectype.lower() in ("python", "executable"):
            optional_widget = self._ui.horizontalLayout_options_placeholder.itemAt(0)
            return optional_widget.widget()
        return None

    @Slot(int)
    def _show_optional_widget(self, row):
        """Adds a ToolSpecOptionalWidget to ui and updates the widget based on specification.

        Args:
            row (int): Active row in tool type combobox
        """
        optional_widget = self._ui.horizontalLayout_options_placeholder.takeAt(0)
        if optional_widget:
            optional_widget.widget().close()
        tooltype = self._ui.comboBox_tooltype.itemText(row)
        optional_widget = self._make_optional_widget(tooltype)
        if optional_widget:
            self._ui.horizontalLayout_options_placeholder.addWidget(optional_widget)
            optional_widget.show()

    def _init_optional_widget(self, specification):
        """Initializes optional widget UI based on specification.

        Args:
            specification (ToolSpecification): Specification that is opened in the editor window
        """
        toolspectype = specification.tooltype.lower()
        opt_widget = self._get_optional_widget(toolspectype)
        if opt_widget:
            opt_widget.init_widget(specification)

    def _make_new_specification(self, spec_name):
        """See base class."""
        # Check that tool type is selected
        if self._ui.comboBox_tooltype.currentIndex() == -1:
            self.show_error("Tool spec type not selected")
            return None
        toolspectype = self._ui.comboBox_tooltype.currentText().lower()
        # Check that Tool Spec has a main program file except for Executable Tool Specs
        main_program_file = self._current_main_program_file()
        if main_program_file is None and toolspectype != "executable":
            self.show_error("Please add a main program file")
            return None
        new_spec_dict = {"name": spec_name, "description": self._spec_toolbar.description(), "tooltype": toolspectype}
        main_prgm_dir, main_prgm_file_name = os.path.split(main_program_file) if main_program_file else ("", "")
        if not main_prgm_dir:
            self.includes_main_path = None
        else:
            self.includes_main_path = os.path.abspath(main_prgm_dir)
        self._label_main_path.setText(self.includes_main_path)
        new_spec_dict["includes"] = [main_prgm_file_name] if main_prgm_file_name else []
        new_spec_dict["includes"] += self._additional_program_file_list()
        new_spec_dict["inputfiles"] = self._input_file_list()
        new_spec_dict["inputfiles_opt"] = self._opt_input_file_list()
        new_spec_dict["outputfiles"] = self._output_file_list()
        # Strip whitespace from args before saving it to JSON
        new_spec_dict["cmdline_args"] = split_cmdline_args(self._ui.lineEdit_args.text())
        new_spec_dict["includes_main_path"] = (
            self.includes_main_path.replace(os.sep, "/") if self.includes_main_path else None
        )
        try:
            new_spec_dict = self.insert_execution_settings(new_spec_dict)
        except NameError:
            self.show_error(f"Creating a {self._ui.comboBox_tooltype.currentText().lower()} Tool spec failed")
            return None
        tool_spec = make_specification(new_spec_dict, self._toolbox.qsettings(), self._toolbox)
        if not tool_spec:
            self.show_error("Creating Tool specification failed")
            return None
        return tool_spec

    def insert_execution_settings(self, d):
        """Insert execution mode settings to Tool spec dictionary.
        For Python Tool specs, these settings give the kernel spec name, is_conda boolean
        and whether to use Jupyter Console or not.

        Args:
            d (dict): Tool spec dictionary where the extra settings (if available) are included
        """
        toolspectype = d["tooltype"]
        opt_widget = self._get_optional_widget(toolspectype)
        if not opt_widget:
            return d
        d["execution_settings"] = opt_widget.add_execution_settings()
        return d

    def _save(self):
        """Saves spec. If successful, also saves all modified program files."""
        if not super()._save():
            return False
        saved = []
        for file_path, doc in self._programfile_documents.items():
            if not doc.isModified():
                continue
            err = self._save_program_file(file_path, doc)
            basename = os.path.basename(file_path)
            if err is None:
                doc.setModified(False)
                saved.append(basename)
                continue
            self.show_error(f"Error while saving {basename}: {err}")
            return True
        if saved:
            saved = ", ".join(saved)
            self._show_status_bar_msg(f"Program files {saved} saved successfully")
        return True

    def _save_program_file(self, file_path, doc):
        """Saves program file."""
        try:
            with open(file_path, "w") as file:
                file.write(doc.toPlainText())
            return None
        except IOError as err:
            return err

    def init_programfile_list(self):
        """List program files in QTreeView."""
        for name in ("Main program file", "Additional program files"):
            item = QStandardItem(name)
            item.setFlags(item.flags() & ~Qt.ItemIsEditable & ~Qt.ItemIsSelectable)
            self.programfiles_model.appendRow(item)
        # Setup 'Main' item
        index = self.programfiles_model.index(0, 0)
        widget = ToolBarWidget("Main program file", self)
        widget.tool_bar.addActions(
            [
                self._ui.actionNew_main_program_file,
                self._ui.actionSelect_main_program_file,
                self._ui.actionRemove_all_program_files,
            ]
        )
        widget.tool_bar.setToolButtonStyle(Qt.ToolButtonIconOnly)
        self._ui.treeView_programfiles.setIndexWidget(index, widget)
        # Setup 'Additional...' item
        index = self.programfiles_model.index(1, 0)
        widget = ToolBarWidget("Additional program files", self)
        widget.tool_bar.addActions(
            [
                self._ui.actionNew_program_file,
                self._ui.actionAdd_program_file,
                self._ui.actionAdd_program_directory,
                self._ui.actionRemove_selected_program_files,
            ]
        )
        widget.tool_bar.setToolButtonStyle(Qt.ToolButtonIconOnly)
        self._ui.treeView_programfiles.setIndexWidget(index, widget)
        self._ui.treeView_programfiles.expandAll()
        tool_tip = (
            '<p>Other program files and/or directories (in addition to the main program file) required by the tool.</p>'
            '<p><span style=" font-weight:600;">Tip</span>: '
            'You can Drag &amp; Drop files and/or directories here from your computer.</p>'
        )
        self.programfiles_model.setData(index, tool_tip, role=Qt.ItemDataRole.ToolTipRole)

    def _current_main_program_file(self):
        """Returns the full path to the current main program file or None if there's no main program."""
        index = self.programfiles_model.index(0, 0)
        root_item = self.programfiles_model.itemFromIndex(index)
        if not root_item.hasChildren():
            return None
        return root_item.child(0).data(Qt.ItemDataRole.UserRole)

    def _additional_program_file_list(self):
        return self.spec_dict.get("includes", [])[1:]

    def populate_main_programfile(self, file_path):
        """Adds the main program item into the program files model.

        Args:
            file_path (str): *absolute* path to main program file
        """
        index = self.programfiles_model.index(0, 0)
        root_item = self.programfiles_model.itemFromIndex(index)
        root_item.removeRows(0, root_item.rowCount())
        if file_path:  # Do only if the spec has a main program (Executable Tool specs may not have one)
            item = QStandardItem(os.path.basename(file_path))
            item.setFlags(item.flags() & ~Qt.ItemIsEditable)
            item.setData(QFileIconProvider().icon(QFileInfo(file_path)), Qt.ItemDataRole.DecorationRole)
            item.setData(file_path, Qt.ItemDataRole.UserRole)
            root_item.appendRow(item)
            QTimer.singleShot(0, self._push_change_main_program_file_command)

    def populate_programfile_list(self, names):
        """Adds additional program files into the program files model.

        Args:
            names (list): List of paths to additional program files
        """
        # Find visible indexes, disconnect 'set program file dirty' slots
        visible = set()
        for item in self.programfiles_model.findItems("", Qt.MatchContains | Qt.MatchRecursive):
            if not item.rowCount():
                index = self.programfiles_model.indexFromItem(item)
                file_path = self._programfile_path_from_index(index)
                if self._ui.treeView_programfiles.isExpanded(index.parent()):
                    visible.add(file_path)
                doc = self._programfile_documents.get(file_path)
                slot = self._programfile_set_dirty_slots.get(file_path)
                if None not in (doc, slot):
                    doc.modificationChanged.disconnect(slot)
        # Repopulate
        index = self.programfiles_model.index(1, 0)
        root_item = self.programfiles_model.itemFromIndex(index)
        root_item.removeRows(0, root_item.rowCount())
        components = _collect_components(names)
        _build_tree(root_item, components)
        # Reexpand visible, connect 'set program file dirty' slots
        self._programfile_set_dirty_slots.clear()
        for item in self.programfiles_model.findItems("", Qt.MatchContains | Qt.MatchRecursive):
            if not item.rowCount():
                index = self.programfiles_model.indexFromItem(item)
                file_path = self._programfile_path_from_index(index)
                if file_path in visible:
                    self._ui.treeView_programfiles.expand(index.parent())
                self._programfile_set_dirty_slots[file_path] = index
                doc = self._programfile_documents.get(file_path)
                if doc is not None:
                    slot = self._programfile_set_dirty_slots[
                        file_path
                    ] = lambda dirty, index=index: self._set_program_file_dirty(index, dirty)
                    doc.modificationChanged.connect(slot)
                    self._set_program_file_dirty(index, doc.isModified())

    def _set_program_file_dirty(self, index, dirty):
        """
        Appends a * to the file name in program files tree view if dirty.

        Args:
            index (QModelIndex): index in program files model
            dirty (bool)
        """
        basename = os.path.basename(index.data(Qt.ItemDataRole.UserRole))
        if dirty:
            basename += "*"
        self.programfiles_model.setData(index, basename, role=Qt.ItemDataRole.DisplayRole)

    def init_io_file_list(self):
        for name in ("Input files", "Optional input files", "Output files"):
            item = QStandardItem(name)
            item.setFlags(item.flags() & ~Qt.ItemIsEditable & ~Qt.ItemIsSelectable)
            self.io_files_model.appendRow(item)
        # Setup 'Input' item
        index = self.io_files_model.index(0, 0)
        widget = ToolBarWidget("Input files", self)
        widget.tool_bar.addActions([self._ui.actionAdd_input_files, self._ui.actionRemove_selected_input_files])
        widget.tool_bar.setToolButtonStyle(Qt.ToolButtonIconOnly)
        self._ui.treeView_io_files.setIndexWidget(index, widget)
        # Setup 'Optional' item
        index = self.io_files_model.index(1, 0)
        widget = ToolBarWidget("Optional input files", self)
        widget.tool_bar.addActions([self._ui.actionAdd_opt_input_files, self._ui.actionRemove_selected_opt_input_files])
        widget.tool_bar.setToolButtonStyle(Qt.ToolButtonIconOnly)
        self._ui.treeView_io_files.setIndexWidget(index, widget)
        # Setup 'Output' item
        index = self.io_files_model.index(2, 0)
        widget = ToolBarWidget("Output files", self)
        widget.tool_bar.addActions([self._ui.actionAdd_output_files, self._ui.actionRemove_selected_output_files])
        widget.tool_bar.setToolButtonStyle(Qt.ToolButtonIconOnly)
        self._ui.treeView_io_files.setIndexWidget(index, widget)

    def _input_file_list(self):
        return self.spec_dict.get("inputfiles", [])

    def _opt_input_file_list(self):
        return self.spec_dict.get("inputfiles_opt", [])

    def _output_file_list(self):
        return self.spec_dict.get("outputfiles", [])

    def _populate_io_files_list(self, index, names):
        root_item = self.io_files_model.itemFromIndex(index)
        root_item.removeRows(0, root_item.rowCount())
        for name in names:
            item = QStandardItem(name)
            item.setData(QFileIconProvider().icon(QFileInfo(name)), Qt.ItemDataRole.DecorationRole)
            root_item.appendRow(item)
        self._ui.treeView_io_files.expand(index)

    def populate_inputfiles_list(self, names):
        """List input files in QTreeView."""
        self.spec_dict["inputfiles"] = names
        index = self.io_files_model.index(0, 0)
        self._populate_io_files_list(index, names)

    def populate_inputfiles_opt_list(self, names):
        """List optional input files in QTreeView."""
        self.spec_dict["inputfiles_opt"] = names
        index = self.io_files_model.index(1, 0)
        self._populate_io_files_list(index, names)

    def populate_outputfiles_list(self, names):
        """List output files in QTreeView."""
        self.spec_dict["outputfiles"] = names
        index = self.io_files_model.index(2, 0)
        self._populate_io_files_list(index, names)

    def connect_signals(self):
        """Connects signals to slots."""
        self._ui.actionNew_main_program_file.triggered.connect(self.new_main_program_file)
        self._ui.actionSelect_main_program_file.triggered.connect(self.browse_main_program_file)
        self._ui.actionRemove_all_program_files.triggered.connect(self.remove_all_program_files)
        self._ui.actionNew_program_file.triggered.connect(self.new_program_file)
        self._ui.actionAdd_program_file.triggered.connect(self.show_add_program_files_dialog)
        self._ui.actionAdd_program_directory.triggered.connect(self.show_add_program_dirs_dialog)
        self._ui.actionRemove_selected_program_files.triggered.connect(self.remove_program_files)
        self._ui.treeView_programfiles.files_dropped.connect(self.add_dropped_program_files)
        self._ui.treeView_programfiles.doubleClicked.connect(self.open_program_file)
        self._ui.actionAdd_input_files.triggered.connect(self.add_inputfiles)
        self._ui.actionRemove_selected_input_files.triggered.connect(self.remove_inputfiles)
        self._ui.actionAdd_opt_input_files.triggered.connect(self.add_inputfiles_opt)
        self._ui.actionRemove_selected_opt_input_files.triggered.connect(self.remove_inputfiles_opt)
        self._ui.actionAdd_output_files.triggered.connect(self.add_outputfiles)
        self._ui.actionRemove_selected_output_files.triggered.connect(self.remove_outputfiles)
        # Enable removing items from QTreeViews by pressing the Delete key
        self._ui.treeView_programfiles.del_key_pressed.connect(self.remove_program_files_with_del)
        self._ui.treeView_io_files.del_key_pressed.connect(self.remove_io_files_with_del)
        # Push undo commands
        self._ui.comboBox_tooltype.currentIndexChanged.connect(self._push_change_tooltype_command)
        self._ui.comboBox_tooltype.currentIndexChanged.connect(self._show_optional_widget)
        self._ui.lineEdit_args.editingFinished.connect(self._push_change_args_command)
        self.io_files_model.dataChanged.connect(self._push_io_file_renamed_command)
        # Selection changed
        self._ui.treeView_programfiles.selectionModel().selectionChanged.connect(
            self._handle_programfile_selection_changed
        )
        self._ui.treeView_io_files.selectionModel().selectionChanged.connect(self._handle_io_file_selection_changed)

    @Slot(int)
    def _push_change_tooltype_command(self, index):
        new_type = TOOL_TYPES[index].lower()
        old_type = self.spec_dict.get("tooltype", "")
        if new_type == old_type:
            return
        self._undo_stack.push(
            ChangeSpecPropertyCommand(self._set_tooltype, new_type, old_type, "change Tool specification type")
        )

    def _set_tooltype(self, value):
        self.spec_dict["tooltype"] = value
        self._ui.textEdit_program.set_lexer_name(value)
        index = next(iter(k for k, t in enumerate(TOOL_TYPES) if t.lower() == value), -1)
        self._ui.comboBox_tooltype.setCurrentIndex(index)
        self.clear_execution_settings(value)

    def clear_execution_settings(self, spec_type):
        """Updates the execution settings dict based on selected tool spec type.
        Sets the default execution settings into self.spec_dict when a Python
        Tool spec type is selected. Removes execution settings from self.spec_dict
        when any other Tool spec type is selected."""
        if "execution_settings" in self.spec_dict:
            self.spec_dict.pop("execution_settings")  # Clear execution settings
        if spec_type == "python":
            self.spec_dict["execution_settings"] = {
                "use_jupyter_console": bool(
                    int(self._toolbox.qsettings().value("appSettings/usePythonKernel", defaultValue="0"))
                ),
                "kernel_spec_name": self._toolbox.qsettings().value("appSettings/pythonKernel", defaultValue=""),
                "env": "",
                "executable": self._toolbox.qsettings().value("appSettings/pythonPath", defaultValue=""),
            }
        elif spec_type == "executable":
            self.spec_dict["execution_settings"] = {"cmd": "", "shell": ""}

    @Slot(int)
    def _push_change_kernel_spec_command(self, index):
        toolspectype = self.spec_dict.get("tooltype", "")
        opt_widget = self._get_optional_widget(toolspectype)
        item = opt_widget.kernel_spec_model.item(index)
        if not item.data():
            new_kernel_spec = ""
        else:
            new_kernel_spec = item.data()["kernel_spec_name"]
        previous_kernel_spec = self.spec_dict["execution_settings"]["kernel_spec_name"]
        if new_kernel_spec == previous_kernel_spec:
            return
        self._undo_stack.push(
            ChangeSpecPropertyCommand(
                self._set_kernel_spec, new_kernel_spec, previous_kernel_spec, "change kernel spec"
            )
        )

    def _set_kernel_spec(self, value):
        self.spec_dict["execution_settings"]["kernel_spec_name"] = value
        opt_widget = self._get_optional_widget("python")
        row = opt_widget.find_index_by_data(value)  # Find row of item in combobox
        if row == -1:
            logging.error(f"Item '{value}' not found in any combobox item's data")
        opt_widget.ui.comboBox_kernel_specs.setCurrentIndex(row)

    @Slot(bool)
    def _push_set_jupyter_console_mode(self, new_value):
        old_value = self.spec_dict["execution_settings"]["use_jupyter_console"]
        if new_value == old_value:
            return
        self._undo_stack.push(
            ChangeSpecPropertyCommand(self._set_jupyter_console_mode, new_value, old_value, "set Jupyter console mode")
        )

    def _set_jupyter_console_mode(self, value):
        self.spec_dict["execution_settings"]["use_jupyter_console"] = value
        toolspectype = self.spec_dict.get("tooltype", "")
        opt_widget = self._get_optional_widget(toolspectype)
        if value:
            opt_widget.ui.radioButton_jupyter_console.setChecked(True)
        else:
            opt_widget.ui.radioButton_python_console.setChecked(True)
        opt_widget.set_ui_for_jupyter_console(not value)

    @Slot()
    def _push_change_executable(self):
        old_value = self.spec_dict["execution_settings"]["executable"]
        toolspectype = self.spec_dict.get("tooltype", "")
        opt_widget = self._get_optional_widget(toolspectype)
        # TODO: Validate executable path?
        new_value = opt_widget.get_executable()
        if new_value == old_value:
            return
        self._undo_stack.push(
            ChangeSpecPropertyCommand(self._set_executable, new_value, old_value, "change path of executable")
        )

    def _set_executable(self, value):
        self.spec_dict["execution_settings"]["executable"] = value
        toolspectype = self.spec_dict.get("tooltype", "")
        opt_widget = self._get_optional_widget(toolspectype)
        opt_widget.set_executable(value)

    @Slot(int)
    def _push_change_shell_command(self, index):
        toolspectype = self.spec_dict.get("tooltype", "")
        opt_widget = self._get_optional_widget(toolspectype)
        new_shell = opt_widget.shells[index] if index != 0 else ""
        old_shell = self.spec_dict["execution_settings"]["shell"]
        if new_shell == old_shell:
            return
        self._undo_stack.push(ChangeSpecPropertyCommand(self._set_shell, new_shell, old_shell, "change shell"))

    def _set_shell(self, value):
        self.spec_dict["execution_settings"]["shell"] = value
        opt_widget = self._get_optional_widget("executable")
        index = next(iter(k for k, t in enumerate(opt_widget.shells) if t.lower() == value), 0)
        opt_widget.ui.comboBox_shell.setCurrentIndex(index)

    @Slot()
    def _push_change_args_command(self):
        old_value = self.spec_dict.get("cmdline_args", [])
        new_value = split_cmdline_args(self._ui.lineEdit_args.text())
        if new_value == old_value:
            return
        self._undo_stack.push(
            ChangeSpecPropertyCommand(self._set_cmdline_args, new_value, old_value, "change command line args")
        )

    def _set_cmdline_args(self, value):
        self.spec_dict["cmdline_args"] = value
        self._ui.lineEdit_args.setText(" ".join(value))

    @Slot()
    def _push_change_executable_command(self):
        old_value = self.spec_dict["execution_settings"]["cmd"]
        opt_widget = self._get_optional_widget("executable")
        new_value = opt_widget.ui.lineEdit_command.text().strip()
        if new_value == old_value:
            return
        self._undo_stack.push(ChangeSpecPropertyCommand(self._set_cmd, new_value, old_value, "change command"))

    def _set_cmd(self, value):
        self.spec_dict["execution_settings"]["cmd"] = value
        opt_widget = self._get_optional_widget("executable")
        opt_widget.ui.lineEdit_command.setText(value)

    @Slot()
    def _push_change_main_program_file_command(self):
        new_value = self._current_main_program_file()
        old_program_files = self.spec_dict.get("includes", [])
        if self.includes_main_path is not None:
            old_program_files = [os.path.join(self.includes_main_path, f) for f in old_program_files]
        old_value = old_program_files[0] if old_program_files else ""
        if new_value is not None:  # Enables removing main program
            if same_path(old_value, new_value):
                return
            new_program_files = old_program_files.copy()
            if new_program_files:
                new_program_files[0] = new_value
            elif new_value:
                new_program_files.append(new_value)
        else:
            new_program_files = []
        self._undo_stack.push(
            ChangeSpecPropertyCommand(
                self._set_program_files, new_program_files, old_program_files, "change main program file"
            )
        )

    def _set_program_files(self, program_files):
        """Sets program files.

        Args:
            program_files (list(str)): List of *absolute* paths
        """
        main_program_file = program_files[0] if program_files else ""
        self.includes_main_path = os.path.dirname(next(iter(f for f in program_files if f), ""))
        additional_program_files = [os.path.relpath(file, self.includes_main_path) for file in program_files[1:]]
        self._set_main_program_file(main_program_file)
        self.populate_programfile_list(additional_program_files)
        self.spec_dict["includes"] = [os.path.basename(main_program_file), *additional_program_files]

    def _set_main_program_file(self, file_path):
        """Sets main program file and dumps its contents into the text edit.

        Args:
            file_path (str): absolute path
        """
        self.populate_main_programfile(file_path)
        self._label_main_path.setText(self.includes_main_path)

    @Slot(QItemSelection, QItemSelection)
    def _handle_programfile_selection_changed(self, _selected, _deselected):
        # Set remove action enabled
        indexes = self._selected_program_file_indexes()
        self._ui.actionRemove_selected_program_files.setEnabled(bool(indexes))
        # Load selected file code on text edit
        current = self._ui.treeView_programfiles.selectionModel().currentIndex()
        if self.programfiles_model.rowCount(current):
            # Not a leaf
            self._clear_program_text_edit()
            return
        self._load_programfile_in_editor(current)

    def _programfile_path_from_index(self, index):
        """Returns absolute path to a file pointed by index.

        Args:
            index (QModelIndex): index

        Returns:
            str: file path
        """
        components = _path_components_from_index(index)
        if not components:
            return ""
        return os.path.join(self.includes_main_path, *components)

    def _clear_program_text_edit(self):
        """Clears contents of the text editor."""
        self._ui.textEdit_program.setDocument(QTextDocument())
        self._ui.textEdit_program.setEnabled(False)
        self._ui.dockWidget_program.setWindowTitle("")

    def _load_programfile_in_editor(self, index):
        """Loads contents of a program file into the text editor.

        Args:
            index (QModelIndex): index in programfiles_model
        """
        file_path = self._programfile_path_from_index(index)
        if not os.path.isfile(file_path):
            self._show_status_bar_msg(f"Program file {file_path} is not valid")
            self._clear_program_text_edit()
            return
        if file_path not in self._programfile_documents:
            try:
                with open(file_path, 'r') as file:
                    text = file.read()
            except (IOError, UnicodeDecodeError) as e:
                self._show_status_bar_msg(str(e))
                return
            document = self._programfile_documents[file_path] = QTextDocument(self._ui.textEdit_program)
            document.setPlainText(text)
            document.setModified(False)
            slot = self._programfile_set_dirty_slots[
                file_path
            ] = lambda dirty, index=index: self._set_program_file_dirty(index, dirty)
            document.modificationChanged.connect(slot)
            document.modificationChanged.connect(self._update_window_modified)
        else:
            document = self._programfile_documents[file_path]
        self._ui.textEdit_program.setDocument(document)
        self._ui.textEdit_program.setEnabled(True)
        self._ui.dockWidget_program.setWindowTitle(os.path.basename(file_path) + "[*]")

    @Slot(bool)
    def browse_main_program_file(self, checked=False):
        """Opens a file dialog where user can select the path of the main program file."""
        # noinspection PyCallByClass, PyTypeChecker, PyArgumentList
        answer = QFileDialog.getOpenFileName(
            self, "Select existing main program file", self._project.project_dir, "*.*"
        )
        file_path = answer[0]
        if not file_path:  # Cancel button clicked
            return
        self.populate_main_programfile(file_path)

    @Slot(bool)
    def new_main_program_file(self, _=False):
        """Creates a new blank main program file."""
        # noinspection PyCallByClass
        answer = QFileDialog.getSaveFileName(self, "Create new main program file", self._project.project_dir)
        file_path = answer[0]
        if not file_path:  # Cancel button clicked
            return
        # Remove file if it exists. getSaveFileName has asked confirmation for us.
        try:
            os.remove(file_path)
        except OSError:
            pass
        try:
            with open(file_path, "w"):
                pass
        except OSError:
            msg = "Please check directory permissions."
            # noinspection PyTypeChecker, PyArgumentList, PyCallByClass
            QMessageBox.information(self, "Creating file failed", msg)
            return
        self.populate_main_programfile(file_path)

    @Slot()
    def new_program_file(self):
        """Let user create a new program file for this tool specification."""
        path = self.includes_main_path if self.includes_main_path else self._project.project_dir
        # noinspection PyCallByClass, PyTypeChecker, PyArgumentList
        dir_path = QFileDialog.getSaveFileName(self, "Create program file", path, "*.*")
        file_path = dir_path[0]
        if file_path == "":  # Cancel button clicked
            return
        # create file. NOTE: getSaveFileName does the 'check for existence' for us
        open(file_path, "w").close()
        self.add_program_files(file_path)

    @Slot(bool)
    def show_add_program_files_dialog(self, checked=False):
        """Let user select program files for this tool specification."""
        path = self.includes_main_path if self.includes_main_path else self._project.project_dir
        # noinspection PyCallByClass, PyTypeChecker, PyArgumentList
        answer = QFileDialog.getOpenFileNames(self, "Add program file", path, "*.*")
        file_paths = answer[0]
        if not file_paths:  # Cancel button clicked
            return
        self.add_program_files(*file_paths)

    @Slot(bool)
    def show_add_program_dirs_dialog(self, checked=False):
        """Let user select a program directory for this tool specification.
        All files and sub-directories will be added to the program files.
        """
        path = self.includes_main_path if self.includes_main_path else self._project.project_dir
        # noinspection PyCallByClass, PyTypeChecker, PyArgumentList
        answer = QFileDialog.getExistingDirectory(self, "Select a directory to add to program files", path)
        file_paths = list()
        for root, _, files in os.walk(answer):
            for file in files:
                file_paths.append(os.path.abspath(os.path.join(root, file)))
        self.add_program_files(*file_paths)

    @Slot(list)
    def add_dropped_program_files(self, file_paths):
        """Adds dropped file paths to Source files list."""
        self.add_program_files(*file_paths)

    def _validate_additional_program_files(self, new_files, old_program_files):
        valid_files = []
        dupes = []
        invalid = []
        for file in new_files:
            if file in old_program_files:
                dupes.append(os.path.basename(file))
                continue
            if self.includes_main_path is not None:
                common_prefix = os.path.commonprefix([os.path.abspath(self.includes_main_path), os.path.abspath(file)])
                if not same_path(common_prefix, self.includes_main_path):
                    invalid.append(os.path.basename(file))
                    continue
            valid_files.append(file)
        if dupes:
            dupes = ", ".join(dupes)
            self._show_status_bar_msg(f"Program file(s) '{dupes}' already added")
        if invalid:
            invalid = ", ".join(invalid)
            self._show_status_bar_msg(f"Program file(s) '{invalid}' not in main directory")
        return valid_files

    def add_program_files(self, *new_files):
        """Appends program files.

        Args:
            *new_files (str): Absolute paths to append.
        """
        old_program_files = self.spec_dict.get("includes", [])
        if self.includes_main_path is not None:
            old_program_files = [os.path.join(self.includes_main_path, f) for f in old_program_files]
        new_files = self._validate_additional_program_files(list(new_files), old_program_files)
        if not new_files:
            return
        new_program_files = old_program_files.copy() + new_files
        self._undo_stack.push(
            ChangeSpecPropertyCommand(
                self._set_program_files, new_program_files, old_program_files, "add program files"
            )
        )

    @Slot()
    def remove_program_files_with_del(self):
        """Adds support for deleting items with the Delete key."""
        self.remove_program_files()

    def _selected_program_file_indexes(self):
        """Returns selected program file indexes in a dict excluding the main program file"""
        indexes = set(self._ui.treeView_programfiles.selectedIndexes())
        # discard main program file
        parent = self.programfiles_model.index(0, 0)
        indexes.discard(self.programfiles_model.index(0, 0, parent))
        # keep only leaves
        return {ind for ind in indexes if not self.programfiles_model.rowCount(ind)}

    @Slot(bool)
    def remove_all_program_files(self, checked=False):
        """Removes all program files including main program. Useful with Executable Tool Specs."""
        self._ui.treeView_programfiles.selectAll()
        inds = set(self._ui.treeView_programfiles.selectedIndexes())
        indexes = {ind for ind in inds if not self.programfiles_model.rowCount(ind)}  # keep only leaves
        if not indexes:
            self._show_status_bar_msg("No program files to remove")
            return
        old_program_files = self.spec_dict.get("includes", [])
        new_program_files = []
        if self.includes_main_path is not None:
            old_program_files = [os.path.join(self.includes_main_path, f) for f in old_program_files]
        self._undo_stack.push(
            ChangeSpecPropertyCommand(
                self._set_program_files, new_program_files, old_program_files, "remove all program files"
            )
        )

    @Slot(bool)
    def remove_program_files(self, checked=False):
        """Removes selected program files from program_file list."""
        indexes = self._selected_program_file_indexes()
        if not indexes:  # Nothing removable selected
            self._show_status_bar_msg("Please select program files to remove")
            return
        removed_files = {os.path.join(*_path_components_from_index(ind)) for ind in indexes}
        old_program_files = self.spec_dict.get("includes", [])
        new_program_files = [f for f in old_program_files if f not in removed_files]
        if self.includes_main_path is not None:
            old_program_files = [os.path.join(self.includes_main_path, f) for f in old_program_files]
            new_program_files = [os.path.join(self.includes_main_path, f) for f in new_program_files]
        self._undo_stack.push(
            ChangeSpecPropertyCommand(
                self._set_program_files, new_program_files, old_program_files, "remove program files"
            )
        )

    @busy_effect
    @Slot(QModelIndex)
    def open_program_file(self, index):
        """Opens a program file in default program."""
        if not index.isValid() or self.programfiles_model.rowCount(index):
            return
        program_file = self._programfile_path_from_index(index)
        _, ext = os.path.splitext(program_file)
        if ext in [".bat", ".exe"]:
            self._toolbox.msg_warning.emit(
                "Sorry, opening files with extension <b>{0}</b> not implemented. "
                "Please open the file manually.".format(ext)
            )
            return
        url = "file:///" + os.path.join(self.includes_main_path, program_file)
        # noinspection PyCallByClass, PyTypeChecker, PyArgumentList
        res = open_url(url)
        if not res:
            self._toolbox.msg_error.emit("Failed to open file: <b>{0}</b>".format(program_file))

    @Slot(bool)
    def add_inputfiles(self, checked=False):
        """Opens a file dialog for selecting input files for this tool specification."""
        msg = (
            "Add an input file or a directory required by your program. Wildcards "
            "<b>are not</b> supported.<br/><br/>"
            "Examples:<br/>"
            "<b>data.csv</b> -> File is copied to the same work directory as the main program.<br/>"
            "<b>input/data.csv</b> -> Creates subdirectory /input to work directory and "
            "copies file data.csv there.<br/>"
            "<b>output/</b> -> Creates an empty directory into the work directory.<br/><br/>"
        )
        # noinspection PyCallByClass, PyTypeChecker, PyArgumentList
        answer = QInputDialog.getText(self, "Add input item", msg, flags=Qt.WindowTitleHint | Qt.WindowCloseButtonHint)
        file_name = answer[0]
        if not file_name:  # Cancel button clicked
            return
        old_files = self.spec_dict.get("inputfiles", [])
        new_files = old_files + [file_name]
        self._undo_stack.push(
            ChangeSpecPropertyCommand(self.populate_inputfiles_list, new_files, old_files, "add input file")
        )

    @Slot(bool)
    def add_inputfiles_opt(self, checked=False):
        """Opens a file dialog for selecting optional input files for this tool specification."""
        msg = (
            "Add optional input files that may be utilized by your program. <br/>"
            "Wildcards are supported.<br/><br/>"
            "Examples:<br/>"
            "<b>data.csv</b> -> If found, file is copied to the same work directory as the main program.<br/>"
            "<b>*.csv</b> -> All found CSV files are copied to the same work directory as the main program.<br/>"
            "<b>input/data_?.dat</b> -> All found files matching the pattern 'data_?.dat' will be copied to <br/>"
            "input/ subdirectory under the same work directory as the main program.<br/><br/>"
        )
        # noinspection PyCallByClass, PyTypeChecker, PyArgumentList
        answer = QInputDialog.getText(
            self, "Add optional input item", msg, flags=Qt.WindowTitleHint | Qt.WindowCloseButtonHint
        )
        file_name = answer[0]
        if not file_name:  # Cancel button clicked
            return
        old_files = self.spec_dict.get("inputfiles_opt", [])
        new_files = old_files + [file_name]
        self._undo_stack.push(
            ChangeSpecPropertyCommand(
                self.populate_inputfiles_opt_list, new_files, old_files, "add optional input file"
            )
        )

    @Slot(bool)
    def add_outputfiles(self, checked=False):
        """Opens a file dialog for selecting output files for this tool specification."""
        msg = (
            "Add output files that will be archived into the Tool results directory after the <br/>"
            "Tool specification has finished execution. Wildcards are supported.<br/><br/>"
            "Examples:<br/>"
            "<b>results.csv</b> -> File is copied from work directory into results.<br/> "
            "<b>*.csv</b> -> All CSV files will copied into results.<br/> "
            "<b>output/*.gdx</b> -> All GDX files from the work subdirectory /output will be copied into <br/>"
            "results /output subdirectory.<br/><br/>"
        )
        # noinspection PyCallByClass, PyTypeChecker, PyArgumentList
        answer = QInputDialog.getText(self, "Add output item", msg, flags=Qt.WindowTitleHint | Qt.WindowCloseButtonHint)
        file_name = answer[0]
        if not file_name:  # Cancel button clicked
            return
        old_files = self.spec_dict.get("outputfiles", [])
        new_files = old_files + [file_name]
        self._undo_stack.push(
            ChangeSpecPropertyCommand(self.populate_outputfiles_list, new_files, old_files, "add output file")
        )

    @Slot(QModelIndex, QModelIndex, list)
    def _push_io_file_renamed_command(self, top_left, bottom_right, roles):
        """Pushes a command to rename input/output files to undo stack.

        Args:
            top_left (QModelIndex): top left index to renamed files
            bottom_right (QModelIndex): bottom right index to renamed files
            roles (list of int):
        """
        if Qt.ItemDataRole.DisplayRole not in roles:
            return
        parent_index = top_left.parent()
        if parent_index.row() == 0:
            old_files = self.spec_dict.get("inputfiles", [])
            callback = self.populate_inputfiles_list
            message = "rename input file"
        elif parent_index.row() == 1:
            old_files = self.spec_dict.get("inputfiles_opt", [])
            callback = self.populate_inputfiles_opt_list
            message = "rename optional input file"
        else:
            old_files = self.spec_dict.get("outputfiles", [])
            callback = self.populate_outputfiles_list
            message = "rename output file"
        new_files = list(old_files)
        for j in range(top_left.column(), bottom_right.column() + 1):
            for i in range(top_left.row(), bottom_right.row() + 1):
                new_files[i] = self.io_files_model.index(i, j, parent_index).data()
        self._undo_stack.push(ChangeSpecPropertyCommand(callback, new_files, old_files, message))

    def _selected_io_file_indexes(self, parent):
        indexes = self._ui.treeView_io_files.selectedIndexes()
        return [ind for ind in indexes if ind.parent() == parent]

    @Slot(QItemSelection, QItemSelection)
    def _handle_io_file_selection_changed(self, _deselected, _selected):
        parent = self.io_files_model.index(0, 0)
        indexes = self._selected_io_file_indexes(parent)
        self._ui.actionRemove_selected_input_files.setEnabled(bool(indexes))
        parent = self.io_files_model.index(1, 0)
        indexes = self._selected_io_file_indexes(parent)
        self._ui.actionRemove_selected_opt_input_files.setEnabled(bool(indexes))
        parent = self.io_files_model.index(2, 0)
        indexes = self._selected_io_file_indexes(parent)
        self._ui.actionRemove_selected_output_files.setEnabled(bool(indexes))

    @Slot(bool)
    def remove_inputfiles(self, checked=False):
        """Removes selected input files from list. Does not remove anything if no items selected."""
        parent = self.io_files_model.index(0, 0)
        indexes = self._selected_io_file_indexes(parent)
        if not indexes:  # Nothing selected
            self._show_status_bar_msg("Please select the input files to remove")
            return
        removed_files = {ind.data(Qt.ItemDataRole.DisplayRole) for ind in indexes}
        old_files = self.spec_dict.get("inputfiles", [])
        new_files = [f for f in old_files if f not in removed_files]
        self._undo_stack.push(
            ChangeSpecPropertyCommand(self.populate_inputfiles_list, new_files, old_files, "remove input files")
        )

    @Slot(bool)
    def remove_inputfiles_opt(self, checked=False):
        """Removes selected optional input files from list. Does not remove anything if no items selected."""
        parent = self.io_files_model.index(1, 0)
        indexes = self._selected_io_file_indexes(parent)
        if not indexes:  # Nothing selected
            self._show_status_bar_msg("Please select the optional input files to remove")
            return
        removed_files = {ind.data(Qt.ItemDataRole.DisplayRole) for ind in indexes}
        old_files = self.spec_dict.get("inputfiles_opt", [])
        new_files = [f for f in old_files if f not in removed_files]
        self._undo_stack.push(
            ChangeSpecPropertyCommand(
                self.populate_inputfiles_opt_list, new_files, old_files, "remove optional input files"
            )
        )

    @Slot(bool)
    def remove_outputfiles(self, checked=False):
        """Removes selected output files from list. Does not remove anything if no items selected."""
        parent = self.io_files_model.index(2, 0)
        indexes = self._selected_io_file_indexes(parent)
        if not indexes:  # Nothing selected
            self._show_status_bar_msg("Please select the output files to remove")
            return
        removed_files = {ind.data(Qt.ItemDataRole.DisplayRole) for ind in indexes}
        old_files = self.spec_dict.get("outputfiles", [])
        new_files = [f for f in old_files if f not in removed_files]
        self._undo_stack.push(
            ChangeSpecPropertyCommand(self.populate_outputfiles_list, new_files, old_files, "remove output files")
        )

    @Slot()
    def remove_io_files_with_del(self):
        """Support for deleting items with the Delete key."""
        self.remove_inputfiles()
        self.remove_inputfiles_opt()
        self.remove_outputfiles()


def _path_components(path):
    """
    Args:
        path(str): a filesystem path, e.g. (/home/user/spine/toolbox/file.py)

    Yields:
        str: path components in 'reverse' order, e.g., file.py, toolbox, spine, user, home
    """
    while path:
        path, component = os.path.split(path)
        yield component


def _collect_components(names):
    """
    Args:
        names (list(str)): list of filepaths

    Returns:
        dict: mapping folders to contents recursively
    """
    components = {}
    for name in names:
        d = components
        for component in reversed(list(_path_components(name))):
            d = d.setdefault(component, {})
    return components


def _build_tree(root, components):
    """Appends rows from given components to given root item.

    Args:
        root (QStandardItem): root item
        components (dict): mapping folders to contents recursively
    """
    nodes = []
    leafs = []
    for parent, children in components.items():
        item = QStandardItem(parent)
        item.setData(parent, Qt.ItemDataRole.UserRole)
        item.setFlags(item.flags() & ~Qt.ItemIsEditable)
        _build_tree(item, children)
        if item.hasChildren():
            nodes.append(item)
            item.setData(QFileIconProvider().icon(QFileIconProvider.IconType.Folder), Qt.ItemDataRole.DecorationRole)
        else:
            item.setData(QFileIconProvider().icon(QFileInfo(parent)), Qt.ItemDataRole.DecorationRole)
            leafs.append(item)
    for item in sorted(nodes, key=methodcaller("text")):
        root.appendRow(item)
    for item in sorted(leafs, key=methodcaller("text")):
        root.appendRow(item)


def _path_components_from_index(index):
    components = []
    while index.parent().isValid():
        components.insert(0, index.data(Qt.ItemDataRole.UserRole))
        index = index.parent()
    return components
