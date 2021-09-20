from . import copier
from . import wrapper

# NOTE: these bindings are generated by the copier, and can be found at the end of `copier.pyx`
#   - we need to use the maps generated mapping SubModExp to PolyModID to return SubModExp instead of PolyModIDs
mast = copier.PyMAST
mval = copier.PyMVal
modules = copier.PyModules
intstr = copier.PyIntStr
gdef = copier.PyGDef
vcell = copier.PyVCell
mtype = copier.PyMType
arg_list = copier.PyArgList


def run(project):
    copier.monomorphize_project(project)
