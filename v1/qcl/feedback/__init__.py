"""
This module stores reports for the user, irrespective of their source.
"""

from .mail import Mailbox
from .report import Report
from .loc import ILoc, BuiltinLoc, TextFileLoc
from .note import INote, LocNote
