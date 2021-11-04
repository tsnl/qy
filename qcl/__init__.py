import json

from . import config
from . import panic
from . import feedback as fb
from . import ast2
from . import types
from . import scheme


def transpile_one_package_set(path_to_root_qyp_file: str):
    qyp_set = ast2.QypSet.load(path_to_root_qyp_file)
    
    #
    # Debug: printing all loaded modules
    #

    print("INFO: Module summary:")
    for qyp_name, qyp in qyp_set.qyp_name_map.items():
        print(f"- qyp {repr(qyp_name)} @ path({repr(qyp.file_path)})")
        for src_file in qyp.iter_src_paths():
            print(f"  - Qy source file @ path({repr(src_file)})")

    #
    # Debug: type tests
    #

    # testing types:
    vec2 = types.StructType([('x', types.FloatType(32)), ('y', types.FloatType(32))])
    vec3 = types.StructType([('x', types.FloatType(32)), ('y', types.FloatType(32)), ('z', types.FloatType(32))])
    print("... Types test:")
    print('\t' + '\n\t'.join(map(str, [
        types.IntType(8, True),
        types.IntType(16, True),
        types.IntType(32, True),
        types.IntType(64, True),
        types.IntType(8, False),
        types.IntType(16, False),
        types.IntType(32, False),
        types.IntType(64, False),
        vec2,
        vec3,
        types.UnionType([('v3', vec3), ('v2', vec2)]),
    ])))

    # testing schemes:
    h_a = types.BoundVarType('a')
    h_b = types.BoundVarType('b')
    scm = scheme.Scheme([h_a, h_b], types.StructType([('x', h_a), ('y', h_b)]))
    instantiate_sub, instantiated_type = scm.instantiate()
    print("... Scheme test:")
    print('\tScheme:            ' + str(scm))
    print('\tInstantiation sub: ' + str(instantiate_sub))
    print('\tInstantiated type: ' + str(instantiated_type))
