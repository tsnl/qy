from . import copier
from . import wrapper

def run(project):
    mp = copier.monomorphize_project(project)
    # assert isinstance(mp, wrapper.MonomorphizerPkg)
    return mp
