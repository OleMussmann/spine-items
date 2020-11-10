######################################################################################################################
# Copyright (C) 2017-2020 Spine project consortium
# This file is part of Spine Items.
# Spine Items is free software: you can redistribute it and/or modify it under the terms of the GNU Lesser General
# Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option)
# any later version. This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
# without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Lesser General
# Public License for more details. You should have received a copy of the GNU Lesser General Public License along with
# this program. If not, see <http://www.gnu.org/licenses/>.
######################################################################################################################

"""
Common models.
Contains a generic File list model and an Item for that model.
Used by the Importer, Gimlet and Tool project items but this may be handy for other project items
as well.

:authors: P. Savolainen (VTT), P. Vennström (VTT), A. Soininen (VTT)
:date:   5.6.2020
"""

import json
from PySide2.QtCore import QAbstractListModel, QFileInfo, QModelIndex, Qt, Signal, QMimeData
from PySide2.QtWidgets import QFileIconProvider
from PySide2.QtGui import QStandardItemModel, QStandardItem, QPixmap, QPainter, QIcon


def _file_label(resource):
    """Picks a label for given file resource."""
    if resource.type_ == "file":
        return resource.path
    if resource.type_ == "database":
        return resource.url
    if resource.type_ in ("transient_file", "file_pattern"):
        label = resource.metadata.get("label")
        if label is None:
            if resource.url is None:
                raise RuntimeError("ProjectItemResource is missing a url and metadata 'label'.")
            return resource.path
        return label
    raise RuntimeError(f"Unknown resource type '{resource.type_}'")


class FileListItem:
    """An item for FileListModel.

    Args:
        label (str): File label; a full path for 'permanent' files or just the basename
            for 'transient' files like Tool's output.
        path (str): Absolute path to the file, empty if not known
        provider_name (str): Name of the project item providing the file
        is_pattern (bool): True if the file is actually a file name pattern
    """

    def __init__(self, label, path, provider_name, is_pattern=False, selected=True):
        self.label = label
        self.path = path
        self.selected = selected
        self.provider_name = provider_name
        self.is_pattern = is_pattern

    @classmethod
    def from_resource(cls, resource):
        """Constructs a FileListItem from ProjectItemResource.

        Args:
            resource (ProjectItemResource): Resource

        Return:
            FileListItem: An item based on given resource

        Raises:
            RuntimeError: If given resource has an unknown type
        """
        is_pattern = False
        if resource.type_ == "file":
            label = resource.path
        elif resource.type_ == "database":
            label = resource.url
        elif resource.type_ == "transient_file":
            label = _file_label(resource)
        elif resource.type_ == "file_pattern":
            label = _file_label(resource)
            is_pattern = True
        else:
            raise RuntimeError(f"Unknown resource type '{resource.type_}'")
        return cls(label, resource.path if resource.url else "", resource.provider.name, is_pattern)

    def exists(self):
        """Returns True if the file exists, False otherwise."""
        return bool(self.path)

    def update(self, resource):
        """Updates item information.

        Args:
            resource (ProjectItemResource): A fresh file resource
        """
        self.path = resource.path if resource.url else ""
        self.provider_name = resource.provider.name
        self.is_pattern = resource.type_ == "file_pattern"


class FileListModel(QAbstractListModel):
    """A model for checkable files to be shown in a file list view."""

    selected_state_changed = Signal(bool, str)
    """Emitted when a file check box state changes."""

    def __init__(self, invalid_resource_types=(), header_label=""):
        super().__init__()
        self._files = list()
        self._invalid_resource_types = invalid_resource_types
        self._header_label = header_label

    @property
    def files(self):
        """All model's file items."""
        return self._files

    def data(self, index, role=Qt.DisplayRole):
        """Returns data associated with given role at given index."""
        if not index.isValid():
            return None
        if role == Qt.DisplayRole:
            return self._files[index.row()].label
        if role == Qt.CheckStateRole:
            return Qt.Checked if self._files[index.row()].selected else Qt.Unchecked
        if role == Qt.DecorationRole:
            path = self._files[index.row()].path
            if path:
                return QFileIconProvider().icon(QFileInfo(path))
        if role == Qt.ToolTipRole:
            item = self._files[index.row()]
            if not item.exists():
                if item.is_pattern:
                    tooltip = f"These files will be generated by {item.provider_name} upon execution."
                else:
                    tooltip = f"This file will be generated by {item.provider_name} upon execution."
            else:
                tooltip = item.path
            return tooltip
        return None

    def flags(self, index):
        """Returns item's flags."""
        if not index.isValid():
            return Qt.NoItemFlags
        item = self._files[index.row()]
        if item.exists():
            return Qt.ItemIsSelectable | Qt.ItemIsUserCheckable | Qt.ItemIsEnabled | Qt.ItemNeverHasChildren
        return Qt.ItemNeverHasChildren

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        """Returns header information."""
        if role != Qt.DisplayRole or orientation != Qt.Horizontal:
            return None
        return self._header_label

    def find_file(self, label):
        """Returns a file item with given label."""
        for item in self._files:
            if item.label == label:
                return item
        raise RuntimeError(f"Could not find file with label '{label}'")

    def labels(self):
        """Returns a list of file labels."""
        return [item.label for item in self._files]

    def mark_as_nonexistent(self, index):
        """Marks item at given index as non-existing."""
        self._files[index.row()].path = ""
        self.dataChanged.emit(index, index, [Qt.ToolTipRole])

    def update(self, resources):
        """Updates the model according to given list of resources."""
        self.beginResetModel()
        items = {item.label: item for item in self._files}
        updated = list()
        new = list()
        for resource in resources:
            if resource.type_ in self._invalid_resource_types:
                continue
            label = _file_label(resource)
            item = items.get(label)
            if item is not None:
                item.update(resource)
                updated.append(item)
            else:
                new.append(FileListItem.from_resource(resource))
        self._files = updated + new
        self.endResetModel()

    def rowCount(self, parent=QModelIndex()):
        """Returns the number of rows in the model."""
        return len(self._files)

    def set_selected(self, label, selected):
        """Changes the given item's selection status.

        Args:
            label (str): item's label
            selected (bool): True to select the item, False to deselect
        """
        row = next((k for k, item in enumerate(self._files) if item.label == label), None)
        if row is None:
            return
        item = self._files[row]
        item.selected = selected
        index = self.index(row, 0)
        self.dataChanged.emit(index, index, [Qt.CheckStateRole])

    def setData(self, index, value, role=Qt.EditRole):
        """Sets data in the model."""
        if role != Qt.CheckStateRole or not index.isValid():
            return False
        checked = value == Qt.Checked
        item = self._files[index.row()]
        self.selected_state_changed.emit(checked, item.label)
        return True

    def set_initial_state(self, selected_items):
        """Fills model with incomplete data; needs a call to :func:`update` to make the model usable."""
        for label, selected in selected_items.items():
            self._files.append(FileListItem(label, label, "", selected=selected))


class InputFileListModel(FileListModel):
    """A model for input files to be shown in a file list view."""

    _invalid_resource_types = ()
    _header_label = "Input files"

    def __init__(self, invalid_resource_types=(), header_label="Input files", checkable=True):
        super().__init__(invalid_resource_types=invalid_resource_types, header_label=header_label)
        self._checkable = checkable

    def flags(self, index):
        flags = super().flags(index) | Qt.ItemIsDragEnabled
        if not self._checkable:
            flags &= ~Qt.ItemIsUserCheckable
        return flags

    def data(self, index, role=Qt.DisplayRole):
        """Returns data associated with given role at given index."""
        if role == Qt.CheckStateRole and not self._checkable:
            return None
        return super().data(index, role=role)

    def mimeData(self, indexes):
        data = QMimeData()
        text = json.dumps(("paths", ";;".join([index.data() for index in indexes])))
        data.setText(text)
        return data


class CommandLineArgItem(QStandardItem):
    def __init__(self, text, rank=None, selectable=False, editable=False, drag_enabled=False, drop_enabled=False):
        super().__init__(text)
        self.setEditable(editable)
        self.setDropEnabled(drop_enabled)
        self.setDragEnabled(drag_enabled)
        self.setSelectable(selectable)
        if rank is not None:
            icon = self._make_icon(rank)
            self.setIcon(icon)

    @staticmethod
    def _make_icon(rank=None):
        pixmap = QPixmap(16, 16)
        pixmap.fill(Qt.white)
        painter = QPainter(pixmap)
        painter.drawText(0, 0, 16, 16, Qt.AlignCenter, f"{rank}:")
        painter.end()
        return QIcon(pixmap)

    def setData(self, value, role=Qt.UserRole + 1):
        if role != Qt.EditRole:
            return super().setData(value, role=role)
        if value != self.data(role=role):
            self.model().replace_arg(self.row(), value)
        return False


class NewCommandLineArgItem(CommandLineArgItem):
    def __init__(self):
        super().__init__("Type new arg here...", selectable=True, editable=True)
        gray_color = qApp.palette().text().color()
        gray_color.setAlpha(128)
        self.setForeground(gray_color)

    def setData(self, value, role=Qt.UserRole + 1):
        if role != Qt.EditRole:
            return super().setData(value, role=role)
        if value != self.data(role=role):
            self.model().append_arg(value)
        return False


class CommandLineArgsModel(QStandardItemModel):
    args_updated = Signal(list)
    _args = []

    def append_arg(self, arg):
        self.args_updated.emit(self._args + [arg])

    def replace_arg(self, row, arg):
        new_args = self._args.copy()
        new_args[row] = arg
        self.args_updated.emit(new_args)

    def mimeData(self, indexes):
        data = QMimeData()
        text = json.dumps(("rows", ";;".join([str(index.row()) for index in indexes])))
        data.setText(text)
        return data

    def dropMimeData(self, data, drop_action, row, column, parent):
        head, contents = json.loads(data.text())
        if head == "rows":
            rows = [int(x) for x in contents.split(";;")]
            head = [arg for k, arg in enumerate(self._args[:row]) if k not in rows]
            body = [self._args[k] for k in rows]
            tail = [arg for k, arg in enumerate(self._args[row:]) if k + row not in rows]
            new_args = head + body + tail
            self.args_updated.emit(new_args)
            return True
        if head == "paths":
            new_args = self._args[:row] + contents.split(";;") + self._args[row:]
            self.args_updated.emit(new_args)
            return True
        return False


class GimletCommandLineArgsModel(CommandLineArgsModel):
    def reset_model(self, args):
        self._args = args
        self.clear()
        self.setHorizontalHeaderItem(0, QStandardItem("Command line arguments"))
        for k, arg in enumerate(args):
            item = CommandLineArgItem(arg, rank=k + 1, editable=True, selectable=True, drag_enabled=True)
            self.appendRow(item)
        self.appendRow(NewCommandLineArgItem())

    def canDropMimeData(self, data, drop_action, row, column, parent):
        return row >= 0


class ToolCommandLineArgsModel(CommandLineArgsModel):
    def reset_model(self, spec_args, tool_args):
        self._args = tool_args
        self.clear()
        self.setHorizontalHeaderItem(0, QStandardItem("Command line arguments"))
        spec_args_root = CommandLineArgItem("Specification arguments")
        tool_args_root = CommandLineArgItem("Tool arguments", drop_enabled=True)
        self.appendRow(spec_args_root)
        self.appendRow(tool_args_root)
        spec_args_children = [CommandLineArgItem(arg, rank=k + 1) for k, arg in enumerate(spec_args)]
        tool_args_children = [
            CommandLineArgItem(arg, rank=k + len(spec_args) + 1, editable=True, selectable=True, drag_enabled=True)
            for k, arg in enumerate(tool_args)
        ]
        tool_args_children.append(NewCommandLineArgItem())
        spec_args_root.appendRows(spec_args_children)
        tool_args_root.appendRows(tool_args_children)

    def canDropMimeData(self, data, drop_action, row, column, parent):
        return parent.data() is not None and row >= 0
