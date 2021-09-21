from collections import defaultdict, namedtuple
import llvmlite.ir as llvm_ir

from qcl import types
from qcl import typer
from qcl import ast
from qcl import monomorphizer as mm


InstantiationRecord = namedtuple(
    "InstantiationRecord",
    ["mono_mod_id", "instantiation_arg_list_id", "sub"]
)

LambdaRegistrationRecord = namedtuple(
    "LambdaRegistrationRecord",
    ["container_mono_mod_id", "lambda_registration_index", "mast_node_id"]
)


class Emitter(object):
    def __init__(self, size_t_width_in_bits) -> None:
        super().__init__()

        self.size_t_width_in_bits = size_t_width_in_bits
        assert self.size_t_width_in_bits in (32, 64)

        # LLVM IR stuff:
        self.llvm_module = llvm_ir.Module("default_qy_module")

        #
        # Initial caches:
        #

        # the instantiation map maps `SubModExp` nodes to `InstantiationRecord` instances.
        # Each record contains the `MonoModID` representing the instantiation, as well as the `ArgListID` used for args.
        self.instantiation_map = defaultdict(list)

        # the instantiation sub map maps `MonoModID` instances to the `typer.substitution.Substitution` used to generate
        # it.
        self.mono_mod_instantiation_sub_map = {}

        # the lambda registration map maps `LambdaExp` nodes to maps from MonoModID to `LambdaRegistrationRecord`
        # instances.
        # Each record contains a `MonoModID` that contains this lambda as well as a registration index.
        self.lambda_registration_map = defaultdict(lambda: defaultdict(list))

        self.build_caches()

        #
        # Declaration maps:
        #

        # the synthetic function map maps `LambdaRegistrationRecord` instances to LLVM function objects.
        # These must be declared.
        self.synthetic_function_map = {}

    def emit_project(self, output_ir_file_path: str):
        self.emit_declarations()
        self.emit_definitions()
        with open(output_ir_file_path, "w") as output_ir_file:
            print(self.llvm_module, file=output_ir_file)

    def build_caches(self):
        # acquiring the total number of MonoModIDs in the system:
        mono_mod_count = mm.modules.count_all_mono_modules()

        # iterating through each MonoModID (order-independent):
        for mono_mod_id in range(mono_mod_count):
            # acquiring MonoMod props:
            source_sub_mod_exp = mm.modules.get_source_sub_mod_exp(mono_mod_id)
            instantiation_arg_list_id = mm.modules.get_instantiation_arg_list_id(mono_mod_id)
            assert isinstance(source_sub_mod_exp, ast.node.SubModExp)

            instantiation_sub = self.compute_instantiation_sub(source_sub_mod_exp, instantiation_arg_list_id)

            # NOTE: already inserted `instantiate_sub` field in `ast.node.GetIdNodeInModuleHelper`
            #       while emitting, if we encounter a GetMonoField MAST node with a parent node with arguments

            # updating `instantiation_map` with information about this MonoModID
            self.instantiation_map[source_sub_mod_exp].append(
                InstantiationRecord(
                    mono_mod_id=mono_mod_id,
                    instantiation_arg_list_id=instantiation_arg_list_id,
                    sub=instantiation_sub
                )
            )
            self.mono_mod_instantiation_sub_map[mono_mod_id] = (
                instantiation_sub
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

                self.lambda_registration_map[ast_exp][mono_mod_id].append(
                    LambdaRegistrationRecord(
                        container_mono_mod_id=mono_mod_id,
                        lambda_registration_index=registered_lambda_ix,
                        mast_node_id=exp_id
                    )
                )

    def emit_declarations(self):
        synthetic_index = 0
        for ast_lambda_exp, mono_mod_lambda_reg_rec_map in self.lambda_registration_map.items():
            for mono_mod_id, lambda_reg_rec_list in mono_mod_lambda_reg_rec_map.items():
                mono_mod_instantiation_sub = self.mono_mod_instantiation_sub_map[mono_mod_id]

                for lambda_reg_rec in lambda_reg_rec_list:
                    assert isinstance(lambda_reg_rec, LambdaRegistrationRecord)

                    self.emit_lambda_declaration(
                        synthetic_index,
                        ast_lambda_exp,
                        lambda_reg_rec,
                        mono_mod_instantiation_sub
                    )
                    synthetic_index += 1

    def emit_lambda_declaration(self, synthetic_index, ast_lambda_exp, lambda_reg_rec, mono_mod_instantiation_sub):
        """
        We map each LambdaRegistrationRecord to an LLVM function such that each Lambda we emit in every MonoModID gets
        declared ahead of time.
        This function declares these functions and stores their data on `builder` and maps on `self`.
        NOTE: if a function accepts implicit arguments, they must be bundled into an extra argument
            - if the argument is less than `size_t` bytes in size, it is passed directly as an argument
            - otherwise, it is passed using a pointer
            - regardless of whether this slot is used, we pass a `size_t` arg to every function called `implicit_args`
        :param synthetic_index: a unique index for this synthetic function
        :param ast_lambda_exp: the polymorphic lambda for which this declaration is.
        :param lambda_reg_rec: the registration record for the monomorphic lambda.
        :param mono_mod_instantiation_sub: a sub used to monomorphize types
        """

        synthetic_name = f"synthetic_function{{index:{synthetic_index},loc:{ast_lambda_exp.loc}}}"

        # checking whether this lambda accepts
        assert isinstance(ast_lambda_exp, ast.node.LambdaExp)
        has_implicit_args = bool(ast_lambda_exp.non_local_name_map)

        native_fn_type = mono_mod_instantiation_sub.rewrite_type(ast_lambda_exp.x_tid)
        assert types.kind.of(native_fn_type) == types.kind.TK.Fn

        for non_local_name, non_local_def_rec in ast_lambda_exp.non_local_name_map.items():
            print(f"- implicit argument: ", non_local_name, flush=True)

        llvm_fn_type = self.emit_llvm_type_for_tid(native_fn_type)
        llvm_fn = llvm_ir.Function(self.llvm_module, llvm_fn_type, name=synthetic_name)

        # store the `llvm_fn` instance on a map associated with this `lambda_reg_rec.mast_node_id`
        #   - when emitting definitions, any instances of this ID evaluate to this `Fn`
        self.synthetic_function_map[lambda_reg_rec] = llvm_fn

    def emit_definitions(self):
        # acquiring the total number of MonoModIDs in the system:
        mono_mod_count = mm.modules.count_all_mono_modules()

        # iterating through each MonoModID (order-independent) to emit lambda definitions and global variable bindings:
        for mono_mod_id in range(mono_mod_count):
            # acquiring MonoMod props:
            source_sub_mod_exp = mm.modules.get_source_sub_mod_exp(mono_mod_id)
            instantiation_arg_list_id = mm.modules.get_instantiation_arg_list_id(mono_mod_id)
            instantiation_sub = self.mono_mod_instantiation_sub_map[mono_mod_id]
            assert isinstance(source_sub_mod_exp, ast.node.SubModExp)

            # iterating through each registered lambda:
            # TODO: implement me

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

    def emit_llvm_type_for_mtype_id(self, mtype_id: int) -> llvm_ir.Type:
        mt_kind = mm.mtype.kind_of_tid(mtype_id)
        if mt_kind == mm.mtype.TypeKind.Unit:
            return llvm_ir.VoidType()
        elif mt_kind == mm.mtype.TypeKind.U1:
            return llvm_ir.IntType(1)
        elif mt_kind == mm.mtype.TypeKind.U8:
            return llvm_ir.IntType(8)
        elif mt_kind == mm.mtype.TypeKind.U16:
            return llvm_ir.IntType(16)
        elif mt_kind == mm.mtype.TypeKind.U32:
            return llvm_ir.IntType(32)
        elif mt_kind == mm.mtype.TypeKind.U64:
            return llvm_ir.IntType(64)
        elif mt_kind == mm.mtype.TypeKind.S8:
            return llvm_ir.IntType(8)
        elif mt_kind == mm.mtype.TypeKind.S16:
            return llvm_ir.IntType(16)
        elif mt_kind == mm.mtype.TypeKind.S32:
            return llvm_ir.IntType(32)
        elif mt_kind == mm.mtype.TypeKind.S64:
            return llvm_ir.IntType(64)
        elif mt_kind == mm.mtype.TypeKind.F32:
            return llvm_ir.FloatType()
        elif mt_kind == mm.mtype.TypeKind.F64:
            return llvm_ir.DoubleType()
        elif mt_kind == mm.mtype.TypeKind.String:
            return self.emit_llvm_type_for_string()
        else:
            raise NotImplementedError(f"Translating unknown MTypeKind to LLVM IR: {mt_kind}")

    def emit_llvm_type_for_tid(self, tid: types.identity.TID):
        tk = types.kind.of(tid)
        if tk == types.kind.TK.Unit:
            return llvm_ir.VoidType()
        elif tk in (types.kind.TK.SignedInt, types.kind.TK.UnsignedInt):
            return llvm_ir.IntType(types.scalar_width_in_bits.of(tid))
        elif tk == types.kind.TK.Float:
            width_in_bits = types.scalar_width_in_bits.of(tid)
            if width_in_bits == 64:
                return llvm_ir.FloatType()
            elif width_in_bits == 32:
                return llvm_ir.DoubleType()
            else:
                raise NotImplementedError(f"Unknown LLVM Type for floating point type F{width_in_bits}")
        elif tk == types.kind.TK.String:
            return self.emit_llvm_type_for_string()
        elif tk == types.kind.TK.Fn:
            native_arg_tid = types.elem.tid_of_fn_arg(tid)
            native_ret_tid = types.elem.tid_of_fn_ret(tid)
            llvm_arg_type = self.emit_llvm_type_for_tid(native_arg_tid)
            llvm_ret_type = self.emit_llvm_type_for_tid(native_ret_tid)
            return self.emit_llvm_type_for_function(llvm_arg_type, llvm_ret_type)
        elif tk in (types.kind.TK.Tuple, types.kind.TK.Struct):
            elem_count = types.elem.count(tid)
            return llvm_ir.LiteralStructType([
                self.emit_llvm_type_for_tid(types.elem.tid_of_field_ix(tid, elem_index))
                for elem_index in range(elem_count)
            ], packed=False)
        else:
            raise NotImplementedError(f"Translating unknown TID into LLVM: {types.spelling.of(tid)}")

    def emit_llvm_type_for_string(self):
        raise NotImplementedError("Translating String type to LLVM")

    def emit_llvm_type_for_function(self, llvm_arg_type, llvm_ret_type):
        implicit_args_type = llvm_ir.IntType(self.size_t_width_in_bits)
        return llvm_ir.FunctionType(llvm_ret_type, (llvm_arg_type, implicit_args_type))

    def compute_instantiation_sub(
            self,
            instantiated_sub_mod_exp: ast.node.SubModExp,
            instantiation_arg_list_id: int
    ):
        remaining_arg_list = instantiation_arg_list_id
        instantiation_sub_map = {}
        formal_tid_list_index = 0
        formal_tid_list = instantiated_sub_mod_exp.own_def_rec_from_typer.scheme.bound_vars
        for template_arg_name, template_arg_def_rec in zip(
                instantiated_sub_mod_exp.template_arg_names,
                instantiated_sub_mod_exp.template_def_list_from_typer
        ):
            # popping an ID from the arg-list:
            assert remaining_arg_list != mm.arg_list.empty_arg_list_id()
            id_from_arg_list = mm.arg_list.head(remaining_arg_list)
            remaining_arg_list = mm.arg_list.tail(remaining_arg_list)

            # filtering only MTypeIDs:
            if isinstance(template_arg_def_rec, typer.definition.TypeRecord):
                actual_tid = self.translate_mtid_to_tid_for_arg_list(id_from_arg_list)
                formal_tid = formal_tid_list[formal_tid_list_index]
                instantiation_sub_map[formal_tid] = actual_tid
                formal_tid_list_index += 1

        return typer.substitution.Substitution(instantiation_sub_map)

    @staticmethod
    def translate_mtid_to_tid_for_arg_list(mtid: int) -> types.identity.TID:
        mtid_kind = mm.mtype.kind_of_tid(mtid)
        if mtid_kind == mm.mtype.TypeKind.Unit:
            return types.get_unit_type()
        elif mtid_kind == mm.mtype.TypeKind.U1:
            return types.get_int_type(1, is_unsigned=True)
        elif mtid_kind == mm.mtype.TypeKind.U8:
            return types.get_int_type(8, is_unsigned=True)
        elif mtid_kind == mm.mtype.TypeKind.U16:
            return types.get_int_type(16, is_unsigned=True)
        elif mtid_kind == mm.mtype.TypeKind.U32:
            return types.get_int_type(32, is_unsigned=True)
        elif mtid_kind == mm.mtype.TypeKind.U64:
            return types.get_int_type(64, is_unsigned=True)
        elif mtid_kind == mm.mtype.TypeKind.S8:
            return types.get_int_type(8, is_unsigned=False)
        elif mtid_kind == mm.mtype.TypeKind.S16:
            return types.get_int_type(16, is_unsigned=False)
        elif mtid_kind == mm.mtype.TypeKind.S32:
            return types.get_int_type(32, is_unsigned=False)
        elif mtid_kind == mm.mtype.TypeKind.S64:
            return types.get_int_type(64, is_unsigned=False)
        elif mtid_kind == mm.mtype.TypeKind.F32:
            return types.get_float_type(32)
        elif mtid_kind == mm.mtype.TypeKind.F64:
            return types.get_float_type(64)
        elif mtid_kind == mm.mtype.TypeKind.Function:
            raise NotImplementedError("TODO: translate MTID functions to TID functions")
        else:
            raise NotImplementedError(f"Translating MTID of kind {mtid_kind} to TID")
