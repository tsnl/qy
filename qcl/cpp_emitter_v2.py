# Rather than emit each Qyp to a different source file set, this emitter simply emits a single C++ source file.

from . import base_emitter


class Emitter(base_emitter.BaseEmitter):
    def __init__(self, out_dir_path) -> None:
        super().__init__()
        self.out_dir_path = out_dir_path
    
    def transpile_one_package_set(self, root_qyp_path, emitter):
        pass
