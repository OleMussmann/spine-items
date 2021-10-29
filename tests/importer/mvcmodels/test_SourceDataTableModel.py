######################################################################################################################
# Copyright (C) 2017-2021 Spine project consortium
# This file is part of Spine Toolbox.
# Spine Toolbox is free software: you can redistribute it and/or modify it under the terms of the GNU Lesser General
# Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option)
# any later version. This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
# without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Lesser General
# Public License for more details. You should have received a copy of the GNU Lesser General Public License along with
# this program. If not, see <http://www.gnu.org/licenses/>.
######################################################################################################################
"""
Contains unit tests for Import editor's SourceDataTableModel.
"""
import unittest
from unittest.mock import MagicMock
from PySide2.QtCore import Qt

from spinedb_api.import_mapping.type_conversion import value_to_convert_spec
from spinedb_api.import_mapping.import_mapping_compat import import_mapping_from_dict
from spine_items.importer.mvcmodels.mappings_model_roles import Role
from spine_items.importer.mvcmodels.mappings_model import MappingsModel
from spine_items.importer.mvcmodels.source_data_table_model import SourceDataTableModel


class TestSourceDataTableModel(unittest.TestCase):
    def test_column_type_checking(self):
        model = SourceDataTableModel()
        model.reset_model([["1", "0h", "2018-01-01 00:00"], ["2", "1h", "2018-01-01 00:00"]])
        model.set_type(0, value_to_convert_spec('float'))
        self.assertEqual(model._column_type_errors, {})
        self.assertEqual(model._row_type_errors, {})
        model.set_type(1, value_to_convert_spec('duration'))
        self.assertEqual(model._column_type_errors, {})
        self.assertEqual(model._row_type_errors, {})
        model.set_type(2, value_to_convert_spec('datetime'))
        self.assertEqual(model._column_type_errors, {})
        self.assertEqual(model._row_type_errors, {})

    def test_row_type_checking(self):
        model = SourceDataTableModel()
        model.reset_model(
            [["1", "1", "1.1"], ["2h", "1h", "2h"], ["2018-01-01 00:00", "2018-01-01 00:00", "2018-01-01 00:00"]]
        )
        model.set_type(0, value_to_convert_spec('float'), orientation=Qt.Vertical)
        self.assertEqual(model._column_type_errors, {})
        self.assertEqual(model._row_type_errors, {})
        model.set_type(1, value_to_convert_spec('duration'), orientation=Qt.Vertical)
        self.assertEqual(model._column_type_errors, {})
        self.assertEqual(model._row_type_errors, {})
        model.set_type(2, value_to_convert_spec('datetime'), orientation=Qt.Vertical)
        self.assertEqual(model._column_type_errors, {})
        self.assertEqual(model._row_type_errors, {})

    def test_column_type_checking_produces_error(self):
        model = SourceDataTableModel()
        model.reset_model([["Not a valid number", "2.4"], ["1", "3"]])
        model.set_type(0, value_to_convert_spec('float'))
        error_index = (0, 0)
        self.assertEqual(len(model._column_type_errors), 1)
        self.assertEqual(model._row_type_errors, {})
        self.assertTrue(error_index in model._column_type_errors)
        self.assertEqual(model.data(model.index(*error_index)), "Not a valid number")

        # if we add a pivoted mapping for the row with the error, the error should not be
        undo_stack = MagicMock()
        mappings_model = MappingsModel(undo_stack, None)
        list_index = self._add_mapping(
            mappings_model, {"map_type": "ObjectClass", "name": {"map_type": "row", "value_reference": 0}}
        )
        model.set_mapping_list_index(list_index)
        self.assertEqual(model.data(model.index(*error_index)), "Not a valid number")

        # or if we add a mapping where there reading starts from a row below the error, the error should not be shown.
        list_index = self._add_mapping(mappings_model, {"map_type": "ObjectClass", "read_start_row": 1})
        model.set_mapping_list_index(list_index)
        self.assertEqual(model.data(model.index(*error_index)), "Not a valid number")
        mappings_model.deleteLater()

    def test_row_type_checking_produces_error(self):
        model = SourceDataTableModel()
        model.reset_model([["1", "2.4"], ["Not a valid number", "3"]])
        model.set_type(1, value_to_convert_spec('float'), orientation=Qt.Vertical)
        error_index = (1, 0)
        self.assertEqual(len(model._row_type_errors), 1)
        self.assertEqual(model._column_type_errors, {})
        self.assertTrue(error_index in model._row_type_errors)
        # Error should only be shown if we have a pivot mapping on that row.
        self.assertEqual(model.data(model.index(*error_index)), "Not a valid number")

        # if we add mapping error should be shown.
        undo_stack = MagicMock()
        mappings_model = MappingsModel(undo_stack, None)
        list_index = self._add_mapping(
            mappings_model, {"map_type": "ObjectClass", "name": {"map_type": "row", "value_reference": 1}}
        )
        model.set_mapping_list_index(list_index)
        self.assertEqual(model.data(model.index(*error_index)), "Not a valid number")
        mappings_model.deleteLater()

    def test_mapping_column_colors(self):
        model = SourceDataTableModel()
        model.reset_model([[1, 2], [3, 4]])
        # column mapping
        undo_stack = MagicMock()
        mappings_model = MappingsModel(undo_stack, None)
        list_index = self._add_mapping(mappings_model, {"map_type": "ObjectClass", "name": 0})
        model.set_mapping_list_index(list_index)
        entity_class_color = self._find_color(list_index, "Object class names")
        self.assertEqual(model.data(model.index(0, 0), role=Qt.BackgroundRole), entity_class_color)
        self.assertEqual(model.data(model.index(1, 0), role=Qt.BackgroundRole), entity_class_color)
        # row not showing color if the start reading row is specified
        list_index = self._add_mapping(mappings_model, {"map_type": "ObjectClass", "name": 0, "read_start_row": 1})
        model.set_mapping_list_index(list_index)
        entity_class_color = self._find_color(list_index, "Object class names")
        self.assertEqual(model.data(model.index(0, 0), role=Qt.BackgroundRole), None)
        self.assertEqual(model.data(model.index(1, 0), role=Qt.BackgroundRole), entity_class_color)
        # row not showing color if the row is pivoted
        list_index = self._add_mapping(
            mappings_model, {"map_type": "ObjectClass", "name": 0, "object": {"map_type": "row", "value_reference": 0}}
        )
        model.set_mapping_list_index(list_index)
        self.assertNotEqual(model.data(model.index(0, 0), role=Qt.BackgroundRole), entity_class_color)
        self.assertEqual(model.data(model.index(1, 0), role=Qt.BackgroundRole), entity_class_color)
        mappings_model.deleteLater()

    def test_mapping_pivoted_colors(self):
        model = SourceDataTableModel()
        model.reset_model([[1, 2], [3, 4]])
        # row mapping
        undo_stack = MagicMock()
        mappings_model = MappingsModel(undo_stack, None)
        list_index = self._add_mapping(
            mappings_model, {"map_type": "ObjectClass", "object": {"map_type": "row", "value_reference": 0}}
        )
        model.set_mapping_list_index(list_index)
        entity_color = self._find_color(list_index, "Object names")
        self.assertEqual(model.data(model.index(0, 0), role=Qt.BackgroundRole), entity_color)
        self.assertEqual(model.data(model.index(0, 1), role=Qt.BackgroundRole), entity_color)
        self.assertEqual(model.data(model.index(1, 0), role=Qt.BackgroundRole), None)
        # column not showing color if the columns is skipped
        list_index = self._add_mapping(
            mappings_model,
            {"map_type": "ObjectClass", "object": {"map_type": "row", "value_reference": 0}, "skip_columns": [0]},
        )
        model.set_mapping_list_index(list_index)
        entity_color = self._find_color(list_index, "Object names")
        self.assertEqual(model.data(model.index(0, 0), role=Qt.BackgroundRole), None)
        self.assertEqual(model.data(model.index(0, 1), role=Qt.BackgroundRole), entity_color)
        self.assertEqual(model.data(model.index(1, 0), role=Qt.BackgroundRole), None)
        mappings_model.deleteLater()

    def test_mapping_column_and_pivot_colors(self):
        model = SourceDataTableModel()
        model.reset_model([[1, 2], [3, 4]])
        # row mapping
        undo_stack = MagicMock()
        mappings_model = MappingsModel(undo_stack, None)
        list_index = self._add_mapping(
            mappings_model, {"map_type": "ObjectClass", "name": 0, "object": {"map_type": "row", "value_reference": 0}}
        )
        model.set_mapping_list_index(list_index)
        # no color showing where row and column mapping intersect
        entity_class_color = self._find_color(list_index, "Object class names")
        entity_color = self._find_color(list_index, "Object names")
        self.assertEqual(model.data(model.index(0, 0), role=Qt.BackgroundRole), None)
        self.assertEqual(model.data(model.index(0, 1), role=Qt.BackgroundRole), entity_color)
        self.assertEqual(model.data(model.index(1, 0), role=Qt.BackgroundRole), entity_class_color)
        self.assertEqual(model.data(model.index(1, 1), role=Qt.BackgroundRole), None)
        mappings_model.deleteLater()

    @staticmethod
    def _find_color(list_index, item_name):
        flattened_mappings = list_index.data(Role.FLATTENED_MAPPINGS)
        row = flattened_mappings.display_names.index(item_name)
        return flattened_mappings.display_colors[row]

    @staticmethod
    def _add_mapping(mappings_model, mapping_dict):
        mapping = import_mapping_from_dict(mapping_dict)
        mappings_model.append_new_table_with_mapping(f"source table {mappings_model.rowCount()}", mapping)
        table_index = mappings_model.index(mappings_model.rowCount() - 1, 0)
        return mappings_model.index(0, 0, table_index)


if __name__ == '__main__':
    unittest.main()
