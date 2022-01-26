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

"""
Contains utilities shared between project items.

:authors: A. Soininen (VTT)
:date:    1.4.2020
"""

from dataclasses import dataclass
from datetime import datetime
from itertools import dropwhile
import json
import os.path
from pathlib import Path
from time import time
from spine_engine.project_item.project_item_resource import file_resource_in_pack, transient_file_resource

EXPORTED_PATHS_FILE_NAME = ".exported.json"
"""Name of the file that stores exporter's internal state."""
EXPORTER_EXECUTION_MANIFEST_FILE_PREFIX = ".export-manifest"
"""Prefix for the temporary files that exporter's executable uses to communicate output paths."""


def database_label(provider_name):
    """Creates a standardized label for database resources.

    Args:
        provider_name (str): resource provider's name

    Returns:
        str: resource label
    """
    return "db_url@" + provider_name


@dataclass
class Database:
    """
    Database specific export settings.
    """

    url: str = ""
    """Database URL."""
    output_file_name: str = ""
    """Output file name; relative to item's data dir."""

    def to_dict(self):
        """
        Serializes :class:`Database` into a dictionary.

        Returns:
            dict: serialized :class:`Database`
        """
        return {"output_file_name": self.output_file_name}

    @staticmethod
    def from_dict(database_dict):
        """
        Deserializes :class:`Database` from a dictionary.

        Args:
            database_dict (dict): serialized :class:`Database`

        Returns:
            Database: deserialized instance
        """
        db = Database()
        db.output_file_name = database_dict["output_file_name"]
        return db


def subdirectory_for_fork(output_file_name, data_dir, output_time_stamps, filter_id_hash):
    """
    Creates scenario/tool based output directory for forked workflow.

    Args:
        output_file_name (str): file name
        data_dir (str): project item's data directory
        output_time_stamps (bool): True if time stamp data should be included in the output path
        filter_id_hash (str): hashed filter id

    Returns:
        str: absolute output path
    """
    if output_time_stamps:
        stamp = datetime.fromtimestamp(time())
        time_stamp = "run@" + stamp.isoformat(timespec="seconds").replace(":", ".")
    else:
        time_stamp = ""
    if filter_id_hash:
        if time_stamp:
            path = os.path.join(data_dir, filter_id_hash + "_" + time_stamp, output_file_name)
        else:
            path = os.path.join(data_dir, filter_id_hash, output_file_name)
    else:
        path = os.path.join(data_dir, time_stamp, output_file_name)
    return path


def exported_files_as_resources(item_name, exported_files, data_dir, databases):
    """Collects exported files from 'export manifests'.

    Args:
        item_name (str): item's name
        exported_files (dict, optional): item's exported files cache
        data_dir (str): item's data directory
        databases (Iterable of Database): item's upstream databases

    Returns:
        tuple: output resources and updated exported files cache
    """
    manifests = collect_execution_manifests(data_dir)
    if manifests is not None:
        names = {db.output_file_name for db in databases}
        manifests = {
            out_file_name: files
            for out_file_name, files in collect_execution_manifests(data_dir).items()
            if out_file_name in names
        }
        exported_files = {name: [str(Path(data_dir, f)) for f in files] for name, files in manifests.items()}
    resources = list()
    if exported_files is not None:
        for db in databases:
            if db.output_file_name:
                files = {f for f in exported_files.get(db.output_file_name, []) if Path(f).exists()}
                if files:
                    resources = [file_resource_in_pack(item_name, db.output_file_name, f) for f in files]
                else:
                    resources.append(transient_file_resource(item_name, db.output_file_name))
    else:
        for db in databases:
            if db.output_file_name:
                resources.append(transient_file_resource(item_name, db.output_file_name))
    return resources, exported_files


def collect_execution_manifests(data_dir):
    """Collects output file names from export manifest files written by exporter's executable item.

    Args:
        data_dir (str): item's data directory

    Returns:
        dict: mapping from output label to list of file paths, or None if no manifest files were found
    """
    manifests = None
    for path in Path(data_dir).iterdir():
        if path.name.startswith(EXPORTER_EXECUTION_MANIFEST_FILE_PREFIX) and path.suffix == ".json":
            with open(path) as manifest_file:
                manifest = json.load(manifest_file)
            for out_file_name, paths in manifest.items():
                relative_paths = list()
                for file_path in paths:
                    p = Path(file_path)
                    if p.is_absolute():
                        # Legacy manifests had absolute paths
                        try:
                            relative_paths.append(p.relative_to(data_dir))
                        except ValueError:
                            # Project may have been moved to another directory (or system)
                            # so data_dir is differs from manifest file content.
                            # Try resolving the relative path manually.
                            parts = tuple(dropwhile(lambda part: part != "output", p.parts))
                            relative_paths.append(str(Path(*parts)))
                    else:
                        relative_paths.append(file_path)
                if manifests is None:
                    manifests = dict()
                manifests.setdefault(out_file_name, list()).extend(paths)
    return manifests
