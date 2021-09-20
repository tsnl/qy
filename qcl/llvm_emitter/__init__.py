from collections import defaultdict, namedtuple
import llvmlite.ir as llvm_ir

from qcl import frontend
from qcl import ast
from qcl import monomorphizer as mm


def run():
    print(">- BEG of LLVM emitter -<")

    # FIXME: need some way to get substitution used to instantiate PolyMod into MonoMod
    #   - can obtain this from ArgList, translating mtype.TID to type.TID
    #   - can then generate a substitution and an AST node reference (for LambdaExp)
    #   - applying sub to existing type yields subbed type, true for any type in MonoModID

    # TODO: implement this PLAN:
    #   - first, declare all synthetic functions (one per lambda) and global variables
    #       - requires info about implicit arguments
    #   - next, process function definitions & global variable initializers

    emitter = Emitter()
    emitter.emit_project()

    print(">- END of LLVM emitter -<")


InstantiationRecord = namedtuple(
    "InstantiationRecord", 
    ["mono_mod_id", "instantiation_arg_list_id", "sub"]
)

LambdaRegistrationRecord = namedtuple(
    "LambdaRegistrationRecord",
    ["container_mono_mod_id", "lambda_registration_index", "mast_node_id"]
)


class Emitter(object):
    def __init__(self) -> None:
        super().__init__()

        # LLVM IR stuff:
        self.llvm_module = llvm_ir.Module()

        # the instantiation map maps `SubModExp` nodes to `InstantiationRecord` instances.
        # Each record contains the `MonoModID` representing the instantiation, as well as the `ArgListID` used for args.
        self.instantiation_map = defaultdict(list)
        
        # the lambda registration map maps `LambdaExp` nodes to `LambdaRegistrationRecord` instances.
        # Each record contains a `MonoModID` that contains this lambda as well as a registration index.
        self.lambda_registration_map = defaultdict(list)

        self._build_caches()
    
    def emit_project(self):
        self._emit_declarations()
        self._emit_definitions()

    def _build_caches(self):
        # acquiring the total number of MonoModIDs in the system:
        mono_mod_count = mm.modules.count_all_mono_modules()

        # iterating through each MonoModID (order-independent):
        for mono_mod_id in range(mono_mod_count):
            # acquiring MonoMod props:
            source_sub_mod_exp = mm.modules.get_source_sub_mod_exp(mono_mod_id)
            instantiation_arg_list_id = mm.modules.get_instantiation_arg_list_id(mono_mod_id)
            assert isinstance(source_sub_mod_exp, ast.node.SubModExp)

            # TODO: acquire the `instantiation_sub`
            #   - can either reverse-compute from ArgListID _OR_
            #   - can also pass the GetFieldInPolyModExp ID that 'owns' each ArgListID
            #       - can then query this expression
            #       - can then get the source AST node
            #       - can then query the type substitution used for the instantiation
            instantiation_sub = None
            raise NotImplementedError("Finish building LLVM emitter caches (read code)")

            # updating `instantiation_map` with information about this MonoModID
            self.instantiation_map[source_sub_mod_exp].append(
                InstantiationRecord(
                    mono_mod_id=mono_mod_id,
                    instantiation_arg_list_id=instantiation_arg_list_id,
                    sub=instantiation_sub
                )
            )
            field_count = mm.modules.get_mono_mod_field_count(mono_mod_id)
            registered_lambda_count = mm.modules.count_registered_lambdas(mono_mod_id)

            print(f"- MonoModID: {mono_mod_id} ({field_count} fields) ({registered_lambda_count} lambdas)")
            print(f"  " f"- module source node: {repr(source_sub_mod_exp)} @ {source_sub_mod_exp.loc}")

            # updating the `lambda_registration_map` by
            # iterating through each registered lambda for this module:
            #   - each lambda must be declared ahead of time with implicit args made explicit
            #   - we assemble 
            for registered_lambda_ix in range(registered_lambda_count):
                # print("  " f"- lambda {registered_lambda_ix}")
                exp_id = mm.modules.get_registered_lambda_at(mono_mod_id, registered_lambda_ix)
                exp_kind = mm.mast.get_node_kind(exp_id)
                ast_exp = mm.mast.get_ast_node(exp_id)
                # print("  " f"  - target exp: {exp_id} (kind: {exp_kind}) (info: {exp_info})")
                # print("  " f"    source exp: {ast_exp}")
                assert exp_kind == mm.mast.NodeKind.EXP_Lambda

                self.lambda_registration_map[ast_exp].append(
                    LambdaRegistrationRecord(
                        container_mono_mod_id=mono_mod_id,
                        lambda_registration_index=registered_lambda_ix,
                        mast_node_id=exp_id
                    )
                )

    def _emit_declarations(self):
        # TODO: 
        #   - iterate through each registered Lambda and declare a synthetic function as required
        #   - associate this synthetic lambda with 
        raise NotImplementedError("_emit_declarations")
        # print("WARNING: skipping `_emit_declarations`")

        synthetic_index = 0
        for ast_lambda_exp, lambda_reg_rec_list in self.lambda_registration_map.items():
            for lambda_reg_rec in lambda_reg_rec_list:
                # TODO: compute `fn_ty` by exporting lambda function type
                # llvm_fn_type = ir.FunctionType(llvm_ret_type, llvm_arg_types)

                # TODO: create a function declaration
                # llvm_fn = ir.Function(self.llvm_module, llvm_fn_type, name=f"synthetic_function_{}")

                # TODO: store the `llvm_fn` instance on a map associated with this `lambda_reg_rec.mast_node_id`
                #   - when emitting definitions, any instances of this ID evaluate to this `Fn` 

                synthetic_index += 1

            pass

    def _emit_definitions(self):
        mono_mod_count = mm.modules.count_all_mono_modules()

        # acquiring the total number of MonoModIDs in the system:
        mono_mod_count = mm.modules.count_all_mono_modules()

        # iterating through each MonoModID (order-independent):
        for mono_mod_id in range(mono_mod_count):
            # acquiring MonoMod props:
            source_sub_mod_exp = mm.modules.get_source_sub_mod_exp(mono_mod_id)
            instantiation_arg_list_id = mm.modules.get_instantiation_arg_list_id(mono_mod_id)
            assert isinstance(source_sub_mod_exp, ast.node.SubModExp)
        
            # iterating through each Bind1VElement in the SubModExp for this MonoModID:
            for field_ix, bind_elem in zip(
                source_sub_mod_exp.mast_bind1v_field_index_mapping_from_monomorphizer,
                source_sub_mod_exp.table.ordered_value_imp_bind_elems
            ):
                assert isinstance(bind_elem, ast.node.Bind1VElem)
                
                field_gdef_id = mm.modules.get_mono_mod_field_gdef_id_at(mono_mod_id, field_ix)
                def_kind = mm.gdef.get_def_kind(field_gdef_id)
                def_target = mm.gdef.get_def_target(field_gdef_id)
                
                print(
                    "  "
                    "  "
                    f"- Bind1VElement `{bind_elem.id_name}`: "
                    f"{{field_ix: {field_ix}, def_kind: {def_kind}, def_target: {def_target}}}"
                )

                if def_kind == mm.gdef.DefKind.ConstTotVal:
                    print(
                        "  " 
                        "  "
                        "  "
                        f"TODO: emit definitions for mm.gdef.{def_kind}"
                    )
                else:
                    raise NotImplementedError("Unknown DefKind stored for Bind1VElement")

