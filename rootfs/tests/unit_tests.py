""" Very quickly written unit tests for a one-time script
"""


import csv
import os
import pytest
import pytest_mock
import shutil
import sys

from swiftclient.service import ClientException, SwiftError, SwiftService, SwiftUploadObject

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

