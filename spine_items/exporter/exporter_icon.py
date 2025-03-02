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
Contains :class:`ExporterIcon`.

:authors: A. Soininen
:date:    10.12.2020
"""

from spinetoolbox.project_item_icon import ProjectItemIcon
from ..animations import ExporterAnimation, AnimationSignaller


class ExporterIcon(ProjectItemIcon):
    def __init__(self, toolbox, icon, icon_color):
        """Exporter icon for the Design View.

        Args:
            toolbox (ToolBoxUI): QMainWindow instance
            icon (str): icon resource path
            icon_color (QColor): Icon's color
        """
        super().__init__(toolbox, icon, icon_color)
        self.animation = ExporterAnimation(self)
        self.animation_signaller = AnimationSignaller()
        self.animation_signaller.animation_started.connect(self.animation.start)
        self.animation_signaller.animation_stopped.connect(self.animation.stop)

    def mouseDoubleClickEvent(self, e):
        """
        Opens transformer's specification editor.

        Args:
            e (QGraphicsSceneMouseEvent): Event
        """
        super().mouseDoubleClickEvent(e)
        item = self._toolbox.project_item_model.get_item(self._name)
        item.project_item.show_specification_window()
