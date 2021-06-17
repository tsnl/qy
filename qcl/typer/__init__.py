"""
This module detects the types of/denoted by terms.
- Wikipedia - Algorithm W (Hindley Milner Type Inference)
- YouTube - C. Hegemann, Type Inference From Scratch https://www.youtube.com/watch?v=ytPAlhnAKro&t=165s
    - implements Algo W for LC + let-bindings, int & bool literals
    - only missing interfaces
Rather than being efficient, this algorithm prioritizes producing traceable output and parallelizability.
- rather than mutating graphs, use bags of immutable symbols
- use theory to its fullest
"""

from qcl import antlr
from qcl import frontend
from qcl import type
from qcl import ast
from qcl import excepts

from . import context
from . import definition
from . import substitution
from . import scheme
from . import seeding
from . import inference


def type_project(project, all_file_module_list):

    # typing occurs in two phases:
    # - seeding: we generate the types of all file modules in terms of free-vars so imports will resolve
    # - inference: we resolve imports, then generate the types of all sub-modules

    root_context = context.make_default_root()

    seeding.seed_project_types(root_context, project, all_file_module_list)
    inference.infer_project_types(project, all_file_module_list)

    # DEBUG: so we can inspect types:
    root_context.print()

'''
# TODO: ensure all tables' contexts define symbols before typing any RHS
# - otherwise, [type] context will not contain other constants' values

# TODO: finish implementing this module (currently copy-pasted from scoper)

class Typer(object):
    def __init__(self, root_context: context.Context):
        super().__init__()
        self.root_context = root_context
        self.top_context = self.root_context
        self.all_modules_in_dd_order = []

    #
    # Context stack management:
    #

    def push_context(self, name, tabular_ast_node, is_closure_boundary=False):
        new_context = context.Context(
            name, tabular_ast_node,
            parent_context=self.top_context, is_closure_boundary=is_closure_boundary
        )
        self.top_context = new_context

    def pop_context(self):
        assert self.top_context is not None
        assert isinstance(self.top_context, Context)
        popped_context = self.top_context
        self.top_context = self.top_context.parent
        return popped_context

    def define(self, name: str, definition: "BaseDefinition"):
        defined_ok = self.top_context.try_define(name, definition)
        if not defined_ok:
            # TODO: replace this with actual error reporting
            print(f"ERROR: `{name}` re-defined in a context at {self.top_context.ast_node.loc}.")
            raise excepts.TyperDetectedError("symbol re-defined")
        else:
            self.all_definitions.append(definition)

    #
    # Type Unification:
    #

    def unify(self, lt_type, rt_type, loc):
        """
        equates LHS and RHS types through substitution in two phases:
        1. first unifies, generating a substitution
        2. then applies substitution to top context by mutation
            - any variables 'out of scope' are excluded from this substitution
        REMEMBER to apply the returned substitution to the top context once composed.
        :param lt_type: the LHS type
        :param rt_type: the RHS type
        :param loc: the location where the unification was attempted
        :return: nothing
        """

        # NOTE: `unify_impl_1` applies substitutions to the current context rather than returning them.
        sub = self.unify_impl_1(lt_type, rt_type)
        if sub is not None:
            sub.apply(self.top_context)
            return sub
        else:
            # TODO: replace this with actual error reporting
            print(f"ERROR: Unification [{lt_type} ⊔ {rt_type}] failed at: {loc}")
            raise excepts.TyperDetectedError("unification failed")
            # return None

    def unify_impl_1(self, lt_type, rt_type):
        if isinstance(lt_type, TVar) or isinstance(rt_type, TVar):
            # - if one argument is a 'var', it is substituted by the other argument.
            # - if both arguments are 'var's, either may be substituted, but only the one.
            if isinstance(lt_type, TVar):
                subbed_var = lt_type
                subbed_by = rt_type
            else:
                subbed_var = rt_type
                subbed_by = lt_type
            assert isinstance(subbed_var, TVar)

            # TODO: does not handle 'occurs' check: how can this be an issue?
            #   - cf `varBind` function in video
            #   - need to track all free type vars in a type
            #   - can then check if 'var' occurs
            #   - cf. 23:30

            # returning a substitution object:
            sub_map = {subbed_var.name: subbed_by}
            sub = Substitution(sub_map)
            return sub

        #
        # empty substitutions for primitives:
        #

        elif isinstance(lt_type, TUnit) and isinstance(rt_type, TUnit):
            return Substitution({})
        elif isinstance(lt_type, TString) and isinstance(rt_type, TString):
            return Substitution({})
        elif isinstance(lt_type, TInteger) and isinstance(rt_type, TInteger):
            if lt_type.width_in_bits != rt_type.width_in_bits:
                print("ERROR: Cannot unify two Integer types with differing `width` without conversion")
                print(f"- re: `{lt_type} ⊔ {rt_type}`")
                return None
            if lt_type.is_signed != rt_type.is_signed:
                print("ERROR: Cannot unify two Integer types with differing `sign` without conversion")
                print(f"- re: `{lt_type} ⊔ {rt_type}`")
                return None
            return Substitution({})
        elif isinstance(lt_type, TFloat) and isinstance(rt_type, TFloat):
            if lt_type.width_in_bits != rt_type.width_in_bits:
                print("ERROR: Cannot unify two Float types with differing `width` without conversion")
                print(f"- re: `{lt_type} ⊔ {rt_type}`")
                return None
            else:
                return Substitution({})

        #
        # unifying argument types:
        #

        elif isinstance(lt_type, TFun) and isinstance(rt_type, TFun):
            # arg_sub = self.unify(lt_type.arg_type, rt_type.arg_type)
            # ret_sub = self.unify(lt_type.ret_type, rt_type.ret_type)

            # arg_sub = self.unify(lt_type.arg_type, rt_type.arg_type)
            # ret_sub = self.unify(lt_type.ret_type, rt_type.ret_type)
            # return arg_sub * ret_sub

            sub_1 = self.unify_impl_1(lt_type.arg_type, rt_type.arg_type)
            if sub_1 is None:
                return None

            lt_ret_type = sub_1.apply(lt_type.ret_type)
            rt_ret_type = sub_1.apply(rt_type.ret_type)

            sub_2 = self.unify_impl_1(lt_ret_type, rt_ret_type)
            if sub_2 is None:
                return None

            # print(sub_1.sub_map)
            # print(sub_2.sub_map)

            return sub_1.compose(sub_2)

        elif isinstance(lt_type, TTuple) and isinstance(rt_type, TTuple):
            if len(lt_type.item_types) != len(rt_type.item_types):
                print(f"ERROR: Cannot unify two tuples of differing element count.")
                print(f"- re: `{lt_type} ⊔ {rt_type}`")
                return None

            last_sub = Substitution({})
            for index, (item1, item2) in enumerate(zip(lt_type.item_types, rt_type.item_types)):
                item1 = last_sub.apply(item1)
                item2 = last_sub.apply(item2)

                item_sub = self.unify_impl_1(item1, item2)
                if item_sub is None:
                    return None

                last_sub = last_sub.compose(item_sub)

            return last_sub

        else:
            # TODO: replace this with actual error reporting.
            print(f"ERROR: Unification `{lt_type} ⊔ {rt_type}` invalid")
            return None

    #
    # Tabular typer helper methods:
    #

    def help_type_table(self, table, dim_unbound_typed_names):
        """
        declares, then types a table in the top context.
        :param table: the table to type
        :param dim_unbound_typed_names: if True, create a field for `x: T` without binding, otherwise error.
        """

        if table.ok:
            declare_ok = self.try_declare_table_elements(table, dim_unbound_typed_names=dim_unbound_typed_names)
            if not declare_ok:
                raise excepts.TyperDetectedError("bad table")

            for element in table.elements:
                self.type_element(element)

    def try_declare_table_elements(self, table, dim_unbound_typed_names=False):
        # checking if the table is valid before polluting contexts
        if not table.ok:
            return False

        declare_ok = True

        # defining all bound symbols:
        bound_names = set()
        for bind_name, binding_element_list in table.binding_elems_map.items():
            if len(binding_element_list) > 1:
                print(f"ERROR: `{bind_name}` bound {len(binding_element_list)} times in one table.")
                declare_ok = False
            else:
                element = binding_element_list[0]

                if isinstance(element, ast.BindOneValueIDElement):
                    definition = BindValueDefinition(element.loc, element.id_name, element)
                elif isinstance(element, ast.BindOneTypeIDElement):
                    definition = BindTypeDefinition(element.loc, element.id_name, element)
                else:
                    raise NotImplementedError(f"Cannot pre-declare element: {element}")

                self.define(bind_name, definition)
                definition.scheme = Scheme(TVar(bind_name))
                bound_names.add(bind_name)

        # defining/reporting all unbound but typed symbols:
        typed_names = set(table.typing_elems_map.keys())
        unbound_typed_names = typed_names - bound_names
        if unbound_typed_names:
            if dim_unbound_typed_names:
                for unbound_typed_name in unbound_typed_names:
                    typing_element_list = table.typing_elems_map[unbound_typed_name]

                    element = typing_element_list[0]

                    if isinstance(element, ast.TypingValueIDElement):
                        definition = DeclareValueDefinition(element.loc, element.id_name, element)
                    elif isinstance(element, ast.TypingTypeIDElement):
                        # illegal typing element?
                        declare_ok = False
                        print(f"ERROR: Illegal typing element: cannot 'dim' a type field in `{table.alias}`")
                        continue
                    else:
                        raise NotImplementedError()

                    self.define(unbound_typed_name, definition)
                    definition.scheme = Scheme(TVar(unbound_typed_name))
            else:
                declare_ok = False

                for unbound_typed_name in unbound_typed_names:
                    print(f"ERROR: `{unbound_typed_name}` typed, but not bound in this table.")

        return declare_ok

    #
    # Typer entry point methods:
    # - first, type the ast module tree
    # - then, type-check all typed modules at once
    #

    def type_ast_module_tree(self, entry_point_ast_module_exp: ast.node.FileModuleExp) -> bool:
        assert isinstance(entry_point_ast_module_exp, ast.node.FileModuleExp)

        typed_ok = True

        module_exp_type = self.type_module_exp(entry_point_ast_module_exp)

        # todo: complete error reporting in typer
        #   - must include mismatched 'kind' values

        # todo: dispatch types of all imported modules here

        return typed_ok

    def type_check_all_typed_modules(self) -> bool:
        return all((type_checker.check_ast_module(module_exp) for module_exp in self.all_modules_in_dd_order))

    #
    # Typer implementation methods:
    #

    def type_module_exp(self, module_exp: ast.ModuleExp) -> Scheme:
        self.all_modules_in_dd_order.append(module_exp)

        self.push_context("module", module_exp)
        self.help_type_table(module_exp.table, dim_unbound_typed_names=False)
        module_context = self.pop_context()

        # TODO: return Module **SCHEME** based on module-context
        # raise NotImplementedError("Typer.type_module_exp")
        return None

    def type_chain_exp(self, chain_exp: ast.ChainExp):
        self.push_context("chain", chain_exp)

        self.help_type_table(chain_exp.table, dim_unbound_typed_names=False)
        if chain_exp.opt_tail is not None:
            tail_type = self.type_exp(chain_exp.opt_tail)
        else:
            tail_type = TUnit()

        self.pop_context()

        return tail_type

    def type_element(self, element: ast.BaseElement):
        if isinstance(element, ast.ForceEvalElement):
            self.type_exp(element.discarded_exp)

        elif isinstance(element, ast.BindOneValueIDElement):
            lhs_definition, lhs_context = self.top_context.lookup(element.id_name, element.loc, shallow_only=True)
            assert isinstance(lhs_definition, BindValueDefinition) and lhs_context is self.top_context
            lhs_type = lhs_definition.scheme.instantiate()
            rhs_type = self.type_exp(element.bind_exp)
            sub = self.unify(lhs_type, rhs_type, element.loc)
            if sub is None:
                raise NotImplementedError("TODO: halt after unification error")
            sub.apply(self.top_context)
            lhs_type = sub.apply(lhs_type)
            rhs_type = sub.apply(rhs_type)

            # NOTE: this may be incorrect, but binding instantiated type monomorphically:
            lhs_definition.scheme = Scheme(lhs_type)

        elif isinstance(element, ast.BindOneTypeIDElement):
            lhs_definition, lhs_context = self.top_context.lookup(element.id_name, element.loc, shallow_only=True)
            assert isinstance(lhs_definition, BindTypeDefinition)
            assert lhs_context is self.top_context
            lhs_type = lhs_definition.scheme.instantiate()
            rhs_type = self.type_type_spec(element.bind_type_spec)
            sub = self.unify(lhs_type, rhs_type, element.loc)
            if sub is None:
                raise NotImplementedError("TODO: halt after unification error")
            sub.apply(self.top_context)
            lhs_type = sub.apply(lhs_type)
            rhs_type = sub.apply(rhs_type)

        elif isinstance(element, ast.TypingTypeIDElement):
            # todo: lookup the typed TID in THIS table
            lhs_definition, lhs_context = self.top_context.lookup(element.id_name, element.loc, shallow_only=True)
            assert isinstance(lhs_definition, BindTypeDefinition) and lhs_context is self.top_context
            lhs_type = lhs_definition.scheme.instantiate()
            interface_type = self.type_type_spec(element.interface_spec)
            # TODO: register type as a piece of this interface, read extension
        elif isinstance(element, ast.TypingValueIDElement):
            lhs_definition, lhs_context = self.top_context.lookup(element.id_name, element.loc, shallow_only=True)
            assert isinstance(lhs_definition, (BindValueDefinition, DeclareValueDefinition)) and lhs_context is self.top_context
            lhs_type = lhs_definition.scheme.instantiate()
            spec_type = self.type_type_spec(element.type_spec)
            sub = self.unify(lhs_type, spec_type, element.loc)
            if sub is None:
                raise NotImplementedError("TODO: halt after unification error")
            sub.apply(self.top_context)
            lhs_type = sub.apply(lhs_type)
            rhs_type = sub.apply(spec_type)

        else:
            print(f"NotImplemented: type_element for {element}")
            assert False

    def type_exp(self, val_exp: ast.BaseExp):
        # setting outer context for later:
        val_exp.x_typer_outer_context = self.top_context

        #
        # determining the type of the expression:
        #

        if isinstance(val_exp, ast.IdExp):
            opt_found, opt_found_context = self.top_context.lookup(val_exp.name, val_exp.loc)
            if opt_found is None:
                print(f"ERROR: Value-ID `{val_exp.name}` not defined in this context: {val_exp.loc}")
                return None
            else:
                found_scheme = opt_found.scheme
                assert isinstance(found_scheme, Scheme)
                return found_scheme.instantiate()

        elif isinstance(val_exp, ast.NumberExp):
            if val_exp.width_in_bits is not None:
                width_in_bits = val_exp.width_in_bits
            else:
                width_in_bits = 32

            if val_exp.is_explicitly_float:
                return TFloat(width_in_bits)
            elif val_exp.is_explicitly_signed:
                return TInteger(width_in_bits, is_signed=True)
            elif val_exp.is_explicitly_unsigned:
                return TInteger(width_in_bits, is_signed=False)
            else:
                return NotImplementedError("Type inference failed for `NumberExp`")

        elif isinstance(val_exp, ast.StringExp):
            # print(f"Scoping string: {repr(val_exp.text)}")
            return TString()

        elif isinstance(val_exp, ast.TupleExp):
            item_types = [self.type_exp(item_exp) for item_exp in val_exp.items]
            return TTuple(item_types)

        elif isinstance(val_exp, ast.ConstructionExp):
            constructed_type = self.type_type_spec(val_exp.constructed_type_spec)
            arg_type = self.type_exp(val_exp.arg_exp)

            # TODO: need to check that `arg_type` can be converted into `constructed_type`

            return constructed_type

        elif isinstance(val_exp, ast.PostfixVCallExp):
            fn_type = self.type_exp(val_exp.called_exp)
            arg_type = self.type_exp(val_exp.arg_exp)
            ret_type = TVar("fn_ret_type")

            # - need to substitute `called_type` with `arg_type -> ret_type`
            # - performed using unification: get most general subst to make the two equal
            #   - unify operator just recursive descent and pattern matching
            #   - note unification is commutative
            #   - then `(unify tyFun (TFun tyArg tyRes))`
            sub = self.unify(fn_type, TFun(arg_type, ret_type), val_exp.loc)
            if sub is None:
                raise NotImplementedError("TODO: halt after unification error")

            # returning the `fn` type since it is updated 'in place'
            sub.apply(self.top_context)
            return sub.apply(ret_type)

        elif isinstance(val_exp, ast.IfExp):
            cond_type = self.type_exp(val_exp.cond_exp)
            then_type = self.type_exp(val_exp.then_exp)
            if val_exp.opt_else_exp is not None:
                else_type = self.type_exp(val_exp.opt_else_exp)
            else:
                else_type = TUnit()

            ret_type = TVar("if")

            sub1 = self.unify(ret_type, then_type, val_exp.loc)
            sub1.apply(self.top_context)
            ret_type = sub1.apply(ret_type)

            sub2 = self.unify(ret_type, sub1.apply(else_type), val_exp.loc)
            sub2.apply(self.top_context)
            ret_type = sub2.apply(ret_type)

            return ret_type

        elif isinstance(val_exp, ast.UnaryExp):
            arg_type = self.type_exp(val_exp.arg_exp)
            raise NotImplementedError("Typing UnaryExp")

        elif isinstance(val_exp, ast.BinaryExp):
            lt_arg_type = self.type_exp(val_exp.lt_arg_exp)
            rt_arg_type = self.type_exp(val_exp.rt_arg_exp)
            raise NotImplementedError("Typing BinaryExp")

        elif isinstance(val_exp, ast.LambdaExp):
            # pushing a new context strip for the function scope:
            self.push_context("lambda", val_exp, is_closure_boundary=True)

            # defining each formal argument, packing arg types:
            arg_type_list = []
            for arg_index, arg_name in enumerate(val_exp.arg_names):
                definition = FormalVArgDefinition(val_exp.loc, arg_name, val_exp, arg_index)
                arg_type = TVar(arg_name)
                definition.scheme = Scheme(arg_type)
                self.define(arg_name, definition)
                arg_type_list.append(arg_type)

            if len(arg_type_list) == 0:
                arg_type = TUnit()
            elif len(arg_type_list) == 1:
                arg_type = arg_type_list[0]
            else:
                arg_type = TTuple(arg_type_list)

            # scoping the body expression:
            return_type = self.type_exp(val_exp.body)

            # popping the top context strip, indicating end of function scope:
            fn_context = self.pop_context()

            # returning the function type:
            return TFun(arg_type, return_type)

        elif isinstance(val_exp, ast.ChainExp):
            return self.type_chain_exp(val_exp)

        elif isinstance(val_exp, ast.ModuleExp):
            return self.type_module_exp(val_exp)

        elif isinstance(val_exp, ast.GetElementByNameExp):
            container_type = self.type_exp(val_exp.container)
            if not isinstance(container_type, TStruct):
                # TODO: replace with actual error reporting
                print(f"ERROR: '.{val_exp.key_name}' container type invalid: `{container_type}` is not a struct.")
                raise excepts.TyperDetectedError("bad .<name> container")

            else:
                found_field_type = container_type.field_map.get(val_exp.key_name, None)
                if found_field_type is None:
                    # TODO: replace with actual error reporting:
                    print(f"ERROR: '.{val_exp.key_name}' key not found in struct")
                    raise excepts.TyperDetectedError("bad .<name> key")

                return found_field_type

        elif isinstance(val_exp, ast.GetElementByIndexExp):
            container_type = self.type_exp(val_exp.container)
            if not isinstance(container_type, TTuple):
                # TODO: replace with actual error reporting
                # TODO: extend check to also cover TArray when implemented
                print(f"ERROR: '.<index>' expression invalid for container type `{container_type}`: "
                      f"expected tuple or array")
                raise excepts.TyperDetectedError("bad .<index> container")

            else:
                if val_exp.index_wrapped_by_parens:
                    raise NotImplementedError("Typing index-wrapped GetElementByIndexExp")
                else:
                    assert isinstance(val_exp.index, ast.NumberExp) and not val_exp.index.is_explicitly_float
                    raise NotImplementedError("Typing GetElementByIndexExp")

        elif val_exp is None:
            assert 0 and "`None` val_exp in scoper."
        else:
            raise NotImplementedError(f"`type_exp` branch for an Unknown Exp: {val_exp.__class__.__name__}")

    def type_type_spec(self, type_spec: ast.BaseTypeSpec):
        if isinstance(type_spec, ast.IdTypeSpec):
            opt_found, opt_found_context = self.top_context.lookup(type_spec.name, type_spec.loc)
            if opt_found is None:
                print(f"ERROR: Type-ID `{type_spec.name}` not defined in this context: {type_spec.loc}")
                return None
            else:
                found_scheme = opt_found.scheme
                assert isinstance(found_scheme, Scheme)

                if found_scheme.bound_var_names:
                    print(f"ERROR: Type-scheme `{type_spec.name}` cannot be used as a type-spec.")
                    return None
                else:
                    detected_type = found_scheme.body_type
                    return detected_type

        elif isinstance(type_spec, ast.UnitTypeSpec):
            return TUnit()

        elif isinstance(type_spec, ast.AdtTypeSpec):
            if not type_spec.table.ok:
                print("ERROR: Bad ADT Type Spec")
                return

            # constructing field-map:
            self.push_context(type_spec.alias, type_spec)
            self.help_type_table(type_spec.table, dim_unbound_typed_names=True)
            field_map = {}
            for element in type_spec.table.elements:
                assert isinstance(element, ast.TypingValueIDElement)
                field_map[element.id_name] = self.type_type_spec(element.type_spec)
            self.pop_context()

            # using field-map, returning a BaseTAdt:
            if type_spec.adt_kind == ast.AdtKind.Structure:
                return TStruct(field_map)
            elif type_spec.adt_kind == ast.AdtKind.TaggedUnion:
                return TEnum(field_map)
            elif type_spec.adt_kind == ast.AdtKind.UntaggedUnion:
                return TUnion(field_map)
            else:
                raise NotImplementedError("Unknown adt_kind")

        elif isinstance(type_spec, ast.InterfaceTypeSpec):
            self.push_context("interface", type_spec)

            self_type_definition = SelfDefinition(type_spec.loc)

            # first, defining `Self` in this context:
            self.define("Self", self_type_definition)

            # second, declaring and typing `requires`:
            self.help_type_table(type_spec.requires_table, dim_unbound_typed_names=True)

            # third, declaring and typing `provides`
            self.help_type_table(type_spec.provides_table, dim_unbound_typed_names=True)

            context = self.pop_context()

            raise NotImplementedError("Typing ast.InterfaceTypeSpec")

        elif isinstance(type_spec, ast.FnSignatureTypeSpec):
            arg_type_spec = self.type_type_spec(type_spec.arg_type_spec)
            ret_type_spec = self.type_type_spec(type_spec.return_type_spec)
            return TFun(arg_type_spec, ret_type_spec)

        else:
            print(f"Ignoring type-spec: {type_spec}")
'''
