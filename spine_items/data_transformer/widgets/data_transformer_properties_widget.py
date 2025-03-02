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
Data transformer properties widget.

:author: A. Soininen
:date:   2.10.2020
"""
from spinetoolbox.widgets.properties_widget import PropertiesWidgetBase
from ..item_info import ItemInfo


class DataTransformerPropertiesWidget(PropertiesWidgetBase):
    """Widget for the Data transformer item properties."""

    def __init__(self, toolbox):
        """
        Args:
            toolbox (ToolboxUI): The toolbox instance where this widget should be embedded
        """
        from ..ui.data_transformer_properties import Ui_Form  # pylint: disable=import-outside-toplevel

        super().__init__(toolbox)
        self.ui = Ui_Form()
        self.ui.setupUi(self)
        model = self._toolbox.filtered_spec_factory_models[ItemInfo.item_type()]
        self.ui.specification_combo_box.setModel(model)
