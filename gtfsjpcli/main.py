#!/usr/bin/env python

import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
sys.path.append(PROJECT_ROOT)
sys.path.append(os.getcwd())

import owcli  # pylint: disable=wrong-import-position

__version__ = "0.1.0"


def main():
    owcli.run(
        cli="gtfsjp",
        version=__version__,
        root=os.path.dirname(os.path.realpath(__file__)),
    )


if __name__ == "__main__":
    main()
