"""
Usage:
    main.py [<project>]

Options:
    <project>   Path to the .uvprojx file (Keil® µVision5 Project File).
                The .uvoptx file (Keil® µVision5 Project Options file) will
                be located automatically as it shall be adjacent to the
                .uvprojx file, having the same filename.
                If this is a directory, .uvprojx is found automatically (if
                multiple found then the latest changed is chosen).
                If not provided then the current working directory is chosen
                as a project directory.
"""
from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING

from docopt import docopt

from .parsers import CMake, Language, UVisionProject

if TYPE_CHECKING:
    from os import DirEntry
    from typing import Iterator

logging.basicConfig(level=logging.INFO)
_LOG = logging.getLogger(__name__)


def main() -> None:
    # region Parse arguments
    arguments = docopt(__doc__)
    project_path: str = arguments["<project>"] or "."

    if not os.path.isfile(project_path):
        with os.scandir(project_path) as dirs:  # type: Iterator[DirEntry]
            projects = [de.path for de in dirs if (de.is_file() and (os.path.splitext(de.name)[1] == ".uvprojx"))]

        if not projects:
            raise FileNotFoundError(f"Could not find any .uvprojx file in '{project_path}'")
        elif len(projects) > 1:
            # Choose the latest file by modification time.
            project_path = max(projects, key=os.path.getmtime)
        else:
            project_path = projects[0]
    project_path = os.path.realpath(project_path)
    # endregion Parse arguments

    _LOG.info(f"Using µVision5 Project File '{project_path}'")

    # Parse uVision project XML files
    uvp = UVisionProject.new(project_path)

    # Generate CMake file and populate it with information from uVision project
    cmake = CMake()

    # Add Assembler properties
    cmake.add_include_paths(uvp.targets[0].build.asm.include_paths, Language.ASM)
    cmake.add_defines(uvp.targets[0].build.asm.defines, Language.ASM)
    cmake.add_undefines(uvp.targets[0].build.asm.undefines, Language.ASM)

    # Add C properties
    cmake.add_include_paths(uvp.targets[0].build.c.include_paths, Language.C)
    cmake.add_defines(uvp.targets[0].build.c.defines, Language.C)
    cmake.add_undefines(uvp.targets[0].build.c.undefines, Language.C)

    # Add source and other files
    for file, lang, comment in uvp.source_files():
        cmake.add_source_files(file.path, lang, comment, file.include_in_build)

    fp_proj_cmake = os.path.join(
        os.path.dirname(uvp.project_file_path), os.path.splitext(os.path.basename(uvp.project_file_path))[0] + ".cmake"
    )
    with open(fp_proj_cmake, "w") as f:
        f.write(str(cmake))
    _LOG.info(f"Generated CMake file '{fp_proj_cmake}'")


if __name__ == "__main__":
    main()
