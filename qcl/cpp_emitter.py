import os.path
import re
import typing as t
from . import ast2
from . import config
from . import base_emitter

#
# Interface:
#


class Emitter(base_emitter.BaseEmitter):
    def __init__(self, rel_output_dir_path: str) -> None:
        super().__init__()
        self.rel_output_dir_path = rel_output_dir_path
        self.abs_output_dir_path = os.path.abspath(rel_output_dir_path)

    def emit_qyp_set(self, qyp_set: ast2.QypSet):
        for qyp_name, src_file_path, source_file in qyp_set.iter_source_files():
            self.emit_single_file(qyp_set, qyp_name, src_file_path, source_file)

    def emit_single_file(self, qyp_set, qyp_name, src_file_path, source_file):
        output_file_stem = os.path.join(
            self.abs_output_dir_path,
            qyp_name,
            os.path.basename(src_file_path)[:-len(config.SOURCE_FILE_EXTENSION)]
        )
        cpp_file_path = f"{output_file_stem}.cpp"
        hpp_file_path = f"{output_file_stem}.hpp"
        print(f"INFO: Generating C/C++ file pair:\n\t{cpp_file_path}\n\t{hpp_file_path}")


#
# C++ generator:
# adapted from https://www.codeproject.com/script/Articles/ViewDownloads.aspx?aid=571645
#

PLACEHOLDER_RE = re.compile(r'\$([^\$]+)\$')


# CodeFragment: t.TypeAlias = t.Union[str, t.List[str]]
CodeFragment = t.Union[str, t.List[str]]


class CppFile(object):
    def __init__(
        self, 
        file_path: str,
        indent_str: str='\t'
    ) -> None:
        super().__init__()
        self.file_path = file_path
        self.file_handle = None
        self.indent_count = 0
        self.indent_str = indent_str

    def __enter__(self):
        self.file_handle = open(self.file_path)

    def __exit__(self, *_):
        assert self.file_handle is not None
        self.file_handle.close()
        self.file_handle = None
 
    def print(self, code_fragment: CodeFragment):
        if isinstance(code_fragment, str):
            lines = code_fragment.splitlines()
        else:
            assert isinstance(code_fragment, list)
            if __debug__:
                for line in code_fragment:
                    assert '\n' not in line
            lines = code_fragment
        
        for line in lines:
            for _ in range(self.indent_count):
                print(self.indent_str, end='')
            print(line, file=self.file_handle)

    def __del__(self):
        assert self.file_handle is None


class Block(object):
    def __init__(self, cpp_file: CppFile, prefix: str, suffix: str = "") -> None:
        super().__init__()
        self.cpp_file = cpp_file
        self.prefix = prefix
        self.suffix = suffix

    def __enter__(self):
        self.cpp_file.print(self.prefix)
        print()

    def __exit__(self, *_):
        pass


# Ooh; is this file-level hiding in Python?		
# __all__ = ["CppFile", "CodeFile"]
