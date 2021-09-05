import abc
import typing as t

from qcl import ast
from qcl import excepts
from qcl import type

from . import substitution
from . import unifier


class DeferredList(object):
    def __init__(self):
        super().__init__()
        self.deferred_order_list = []
        self.unsolved_deferred_order_list = []

    def add(self, deferred_order):
        self.deferred_order_list.append(deferred_order)

        unsolved_tuple = (
            len(self.deferred_order_list) - 1,
            deferred_order
        )
        self.unsolved_deferred_order_list.append(unsolved_tuple)

    def solve_step(self, all_sub) -> t.Tuple[bool, substitution.Substitution]:
        any_solved = False

        if self.unsolved_deferred_order_list:
            still_unsolved_index_list = []
            for unsolved_tuple in self.unsolved_deferred_order_list:
                original_index, deferred_order = unsolved_tuple

                assert isinstance(deferred_order, BaseDeferredOrder)
                order_solved, order_sub = deferred_order.solve(all_sub)

                if not order_solved:
                    still_unsolved_index_list.append(unsolved_tuple)

                any_solved = any_solved or order_solved
                all_sub = order_sub.compose(all_sub)

            self.unsolved_deferred_order_list = still_unsolved_index_list

        return any_solved, all_sub

    def check_all_solved(self):
        return not self.unsolved_deferred_order_list

    def unsolved_str(self):
        return '\n'.join((
            f"- {str(order)}"
            for order_index, order in self.unsolved_deferred_order_list
        ))

    def rewrite_orders_with(self, sub: "substitution.Substitution"):
        # NOTE: Possible Optimization:
        #   - only rewrite unsolved orders, letting data in solved ones go stale.
        #   - would render print-outs useless
        #       - could update in order's `solve` method
        for deferred_order in self.deferred_order_list:
            for elem_index, elem_tid in enumerate(deferred_order.elem_tid_list):
                deferred_order.elem_tid_list[elem_index] = sub.rewrite_type(elem_tid)


#
#
# DeferredOrder:
# - if we can't make typing judgements right away, we punt until later.
# - these orders must be resolved iteratively and repeatedly until a fixed-point occurs.
#
#

class BaseDeferredOrder(object, metaclass=abc.ABCMeta):
    def __init__(self, loc, elem_tid_list):
        super().__init__()
        self.loc = loc
        self.elem_tid_list = elem_tid_list

    def rw(self, sub):
        for i in range(len(self.elem_tid_list)):
            self.elem_tid_list[i] = sub.rewrite_type(self.elem_tid_list[i])

    @abc.abstractmethod
    def solve(self, all_sub: substitution.Substitution) -> t.Tuple[bool, substitution.Substitution]:
        """
        :return: a tuple of...
            - True if solved, else False
            - the substitution to compose
        """

    def extra_args_str(self):
        return ""

    def __str__(self):
        name = f"{self.__class__.__name__}[{self.extra_args_str()}]"
        args = (
            type.spelling.of(elem_tid)
            for elem_tid in self.elem_tid_list
        )
        return f"{name}({', '.join(args)}) @ {self.loc}"


class TypeCastDeferredOrder(BaseDeferredOrder):
    def __init__(self, loc, dst_tid, src_tid):
        super().__init__(loc, [dst_tid, src_tid])

    @property
    def dst_tid(self):
        return self.elem_tid_list[0]

    @property
    def src_tid(self):
        return self.elem_tid_list[1]

    def solve(self, sub: substitution.Substitution) -> t.Tuple[bool, substitution.Substitution]:
        return self.cast(
            sub.rewrite_type(self.src_tid),
            sub.rewrite_type(self.dst_tid),
            sub
        )

    @staticmethod
    def cast(src_tid, dst_tid, sub):
        solved = True

        src_tk = type.kind.of(src_tid)
        dst_tk = type.kind.of(dst_tid)

        simple_monomorphic_tk_set = {
            type.kind.TK.Unit,
            type.kind.TK.String
        }
        number_tk_set = {
            type.kind.TK.SignedInt,
            type.kind.TK.UnsignedInt,
            type.kind.TK.Float
        }
        simple_window_tk_set = {
            type.kind.TK.Pointer,
            type.kind.TK.Array
        }
        slice_src_tk_set = {
            type.kind.TK.Slice,
            type.kind.TK.Array
        }
        var_tk_set = {
            type.kind.TK.FreeVar,
            type.kind.TK.BoundVar,
        }

        # comparing src_tid and dst_tid to ensure they can be inter-converted.
        #   - Unit only from Unit, String only from String
        #   - SignedInt, UnsignedInt, Float from SignedInt, UnsignedInt, Float (numbers interchangeable)
        #   - Struct, Tuple from Struct, Tuple
        #       - need to perform element-wise conversion
        #       - length mismatch from tuple or struct unacceptable <=> mostly identity operation on packed bytes
        #   - Enum, Union from other Enum, Union
        #       - can construct enum/union branch using `EnumType:variant` or `UnionType:variant` (syntax WIP)
        #   - Array from Array only, Pointer from Pointer only, Slice from Array or Slice
        #       - NOTE: can unify content type for all three containers: implies that `reinterpret_cast`-type behavior
        #         is a totally different expression/function.
        #       - NOTE: must also ensure `mut` specifier matches: can convert from `mut` to non-mut but not vice-versa.
        #   - cannot cast any other type kind

        # case 1: String, Unit
        if dst_tk in simple_monomorphic_tk_set:
            if src_tid != dst_tid:
                TypeCastDeferredOrder.raise_cast_error(src_tid, dst_tid)

        # case 2: numbers
        elif dst_tk in number_tk_set:
            if src_tk not in number_tk_set:
                TypeCastDeferredOrder.raise_cast_error(src_tid, dst_tid)

        # case 3: array/ptr
        elif dst_tk in simple_window_tk_set:
            # assigning the 'mem window info' from the cast argument:

            # checking that we are only converting array -> array and ptr -> ptr
            if src_tk != dst_tk:
                TypeCastDeferredOrder.raise_cast_error(
                    src_tid, dst_tid,
                    "cannot convert array to pointer or vice-versa"
                )

            # checking both share the same mutability:
            dst_is_mut = bool(type.mem_window.is_mut(dst_tid))
            src_is_mut = bool(type.mem_window.is_mut(src_tid))
            if dst_is_mut and not src_is_mut:
                TypeCastDeferredOrder.raise_cast_error(
                    src_tid, dst_tid,
                    "cannot cast immutable window to a mutable one"
                )

            # attempting to unify content types => error if failed.
            if type.elem.tid_of_ptd(dst_tid) != type.get_unit_type():
                ptd_unify_sub = unifier.unify(
                    type.elem.tid_of_ptd(src_tid),
                    type.elem.tid_of_ptd(dst_tid)
                )
                sub = ptd_unify_sub.compose(sub)

            # if both arrays, check if length is identical:
            if dst_tk == type.kind.TK.Array:
                # TODO: need to further validate the arrays are of the same length
                # NOTE: can also determine this in 'basic checks' later
                pass

            # TODO: verify that index types are convertible

        # case 4: slice
        elif dst_tk == type.kind.TK.Slice:
            if src_tk not in slice_src_tk_set:
                TypeCastDeferredOrder.raise_cast_error(src_tid, dst_tid)

            # TODO: verify that index types are convertible using `cast`

        # TODO: handle tuples/structs (using recursive conversion)
        elif dst_tk == type.kind.TK.Tuple:
            raise NotImplementedError("Handling TypeCastDeferredOrder for tuple")
        elif dst_tk == type.kind.TK.Struct:
            raise NotImplementedError("Handling TypeCastDeferredOrder for struct")

        # case 5: still variables: defer
        elif src_tk in var_tk_set or dst_tk in var_tk_set:
            solved = False

        # case 6: ensure no inference errors
        else:
            TypeCastDeferredOrder.raise_cast_error(src_tid, dst_tid)

        return solved, sub

    @staticmethod
    def raise_cast_error(src_tid, dst_tid, more=None):
        spell_src = type.spelling.of(src_tid)
        spell_dst = type.spelling.of(dst_tid)
        msg_suffix = f"Cannot cast to {spell_dst} from {spell_src}"
        if more is not None:
            msg_suffix += f": {more}"
        raise excepts.TyperCompilationError(msg_suffix)


class UnaryOpDeferredOrder(BaseDeferredOrder):
    pos_neg_overload_map = None

    def __init__(self, loc, unary_op, arg_tid, ret_tid):
        super().__init__(loc, [arg_tid, ret_tid])
        self.unary_op = unary_op

    @property
    def proxy_arg_tid(self):
        return self.elem_tid_list[0]

    @property
    def proxy_ret_tid(self):
        return self.elem_tid_list[1]

    def solve(self, sub: substitution.Substitution) -> t.Tuple[bool, substitution.Substitution]:
        # lazily initializing the static 'pos_neg_overload_map':
        #   - we cannot instantiate this in the global scope for Python module initialization reasons
        if UnaryOpDeferredOrder.pos_neg_overload_map is None:
            UnaryOpDeferredOrder.pos_neg_overload_map = UnaryOpDeferredOrder.new_pos_neg_overload_map()
            assert UnaryOpDeferredOrder.pos_neg_overload_map is not None

        # deferring if the argument TID is a variable:
        if is_var_tid(self.proxy_arg_tid):
            return False, substitution.empty

        # handling Pos/Neg:
        if self.unary_op in (ast.node.UnaryOp.Neg, ast.node.UnaryOp.Pos):
            # looking up the return TID based on argument TIDs:
            key = (self.unary_op, self.proxy_arg_tid)
            opt_ret_tid = UnaryOpDeferredOrder.pos_neg_overload_map.get(key, None)
            if opt_ret_tid is not None:
                return (
                    True,
                    unifier.unify(opt_ret_tid, self.proxy_ret_tid)
                )
            else:
                self.raise_call_error()

        # handling DeRef: overloaded on `mut[]` and `[]`:
        elif self.unary_op == ast.node.UnaryOp.DeRef:
            arg_tk = type.kind.of(self.proxy_arg_tid)
            assert not is_var_tk(arg_tk)

            if arg_tk == type.kind.TK.Pointer:
                # irrelevant whether pointer is mutable or not.

                new_sub = unifier.unify(
                    self.proxy_ret_tid,
                    type.elem.tid_of_ptd(self.proxy_arg_tid)
                )
                sub = new_sub.compose(sub)

                return (
                    False,
                    sub
                )
            else:
                self.raise_call_error()

        else:
            raise NotImplementedError(f"NotImplemented: solve for unary op {self.unary_op}")

    def raise_call_error(self):
        unary_op = self.unary_op
        arg_tid = self.proxy_arg_tid

        unary_op_spelling = {
            ast.node.UnaryOp.Pos: '+',
            ast.node.UnaryOp.Neg: '-',
            ast.node.UnaryOp.LogicalNot: 'not',
            ast.node.UnaryOp.DeRef: '@',
        }[unary_op]

        arg_spelling = type.spelling.of(arg_tid)

        msg_suffix = f"invalid args for unary op call: {unary_op_spelling}({arg_spelling})"

        raise excepts.TyperCompilationError(msg_suffix)

    @staticmethod
    def new_pos_neg_overload_map():
        return {
            (unary_operator, type.get_int_type(i, is_unsigned=src_sgn)):
                type.get_int_type(i, is_unsigned=False)
            for i in (
                8,
                16,
                32,
                64,
                128
            )
            for src_sgn in (
                False,
                True
            )
            for unary_operator in (
                ast.node.UnaryOp.Pos,
                ast.node.UnaryOp.Neg
            )
        } | {
            (unary_operator, type.get_float_type(i)): type.get_float_type(i)
            for i in (
                32, 64
            )
            for unary_operator in (
                ast.node.UnaryOp.Pos,
                ast.node.UnaryOp.Neg
            )
        }


class BinaryOpDeferredOrder(BaseDeferredOrder):
    # FIXME: need to infer BinaryOp arguments based on either left or right, not both
    overload_map = None
    uniformly_typed_operators = None

    def __init__(self, loc, binary_op, lt_arg_tid, rt_arg_tid, ret_tid):
        super().__init__(loc, [lt_arg_tid, rt_arg_tid, ret_tid])
        self.binary_op = binary_op

    def extra_args_str(self):
        return self.get_bin_op_spelling(self.binary_op)

    @property
    def proxy_lt_arg_tid(self):
        return self.elem_tid_list[0]

    @proxy_lt_arg_tid.setter
    def proxy_lt_arg_tid(self, val):
        self.elem_tid_list[0] = val

    @property
    def proxy_rt_arg_tid(self):
        return self.elem_tid_list[1]

    @proxy_rt_arg_tid.setter
    def proxy_rt_arg_tid(self, val):
        self.elem_tid_list[1] = val

    @property
    def proxy_ret_tid(self):
        return self.elem_tid_list[2]

    @proxy_ret_tid.setter
    def proxy_ret_tid(self, val):
        self.elem_tid_list[2] = val

    def solve(self, sub: substitution.Substitution) -> t.Tuple[bool, substitution.Substitution]:
        # Initializing overload map lazily:
        if BinaryOpDeferredOrder.overload_map is None:
            BinaryOpDeferredOrder.overload_map = BinaryOpDeferredOrder.new_half_overload_map()
            BinaryOpDeferredOrder.uniformly_typed_operators = {
                ast.node.BinaryOp.Pow,
                ast.node.BinaryOp.Mul,
                ast.node.BinaryOp.Div,
                ast.node.BinaryOp.Rem,
                ast.node.BinaryOp.Add,
                ast.node.BinaryOp.Sub
            }
            assert isinstance(BinaryOpDeferredOrder.overload_map, dict)

        # Deferring if arg types & return type are ALL variables
        #   - if either arg is a variable, we can still infer types for type-symmetric binary operators.
        #   - if both args are variables but return type is not, we can infer all types for symmetric operators.
        args_are_vars = (is_var_tid(self.proxy_lt_arg_tid) and is_var_tid(self.proxy_rt_arg_tid))
        ret_is_var = is_var_tid(self.proxy_ret_tid)
        if args_are_vars and ret_is_var:
            return False, substitution.empty

        # Whether lhs or rhs is var or not, we must still unify the types
        # of symmetrically typed binary operators, i.e. all of the binary operators.
        new_sub = unifier.unify(self.proxy_lt_arg_tid, self.proxy_rt_arg_tid)
        sub = new_sub.compose(sub)

        # first, assuming no new information was gained this pass:
        no_new_info_this_pass = True

        def update_with_sub(update_sub):
            nonlocal sub, self
            nonlocal no_new_info_this_pass
            sub = update_sub.compose(sub)
            # self.proxy_ret_tid = sub.rewrite_type(self.proxy_ret_tid)
            # self.proxy_lt_arg_tid = sub.rewrite_type(self.proxy_lt_arg_tid)
            # self.proxy_rt_arg_tid = sub.rewrite_type(self.proxy_rt_arg_tid)
            no_new_info_this_pass = False

        # Trying to look up and solve with the left argument:
        if not is_var_tid(self.proxy_lt_arg_tid):
            key = (
                self.binary_op,
                self.proxy_lt_arg_tid
            )
            ret_tid = BinaryOpDeferredOrder.overload_map.get(key, None)
            if ret_tid is None:
                self.raise_call_error()
            ret_sub = unifier.unify(self.proxy_ret_tid, ret_tid)
            update_with_sub(ret_sub)

        # Trying to look and solve with the right argument:
        if not is_var_tid(self.proxy_rt_arg_tid):
            key = (
                self.binary_op,
                self.proxy_rt_arg_tid
            )
            ret_tid = BinaryOpDeferredOrder.overload_map.get(key, None)
            if ret_tid is None:
                self.raise_call_error()
            ret_sub = unifier.unify(self.proxy_ret_tid, ret_tid)
            update_with_sub(ret_sub)

        # For arithmetic operators, we can infer the type of all arguments using just the return type,
        # since they form a closed group:
        if self.binary_op in self.uniformly_typed_operators:
            lt_sub = unifier.unify(self.proxy_lt_arg_tid, self.proxy_ret_tid)
            update_with_sub(lt_sub)
            rt_sub = unifier.unify(self.proxy_rt_arg_tid, self.proxy_ret_tid)
            update_with_sub(rt_sub)

        # Returning:
        success = not no_new_info_this_pass
        return success, sub

    def raise_call_error(self):
        binary_op = self.binary_op
        lt_arg_tid = self.proxy_lt_arg_tid
        rt_arg_tid = self.proxy_rt_arg_tid

        binary_op_spelling = self.get_bin_op_spelling(binary_op)

        lt_arg_spelling = type.spelling.of(lt_arg_tid)
        rt_arg_spelling = type.spelling.of(rt_arg_tid)

        msg_suffix = f"invalid args for binary op call: {binary_op_spelling}({lt_arg_spelling}, {rt_arg_spelling})"

        raise excepts.TyperCompilationError(msg_suffix)

    @staticmethod
    def get_bin_op_spelling(binary_op):
        return {
            ast.node.BinaryOp.Pow: '^',
            ast.node.BinaryOp.Mul: '*',
            ast.node.BinaryOp.Div: '/',
            ast.node.BinaryOp.Rem: '%',
            ast.node.BinaryOp.Add: '+',
            ast.node.BinaryOp.Sub: '-',
            ast.node.BinaryOp.LT: '<',
            ast.node.BinaryOp.GT: '>',
            ast.node.BinaryOp.LEq: '<=',
            ast.node.BinaryOp.GEq: '>=',
            ast.node.BinaryOp.Eq: '=',
            ast.node.BinaryOp.NE: '<>',
            ast.node.BinaryOp.LogicalAnd: 'and',
            ast.node.BinaryOp.LogicalOr: 'or'
        }[binary_op]

    """
    Overload maps for symmetric binary operations are 'halved':
    - map 1 argument type to 1 return type
    - lookups occur for either/both arguments to infer all 3 types: lhs, rhs, return type. 
    """

    @staticmethod
    def new_half_overload_map():
        overload_map = {}

        int_arithmetic_map = BinaryOpDeferredOrder.new_int_arithmetic_half_overload_map()
        overload_map |= int_arithmetic_map

        overload_map |= BinaryOpDeferredOrder.new_int_comparison_half_overload_map()

        overload_map |= BinaryOpDeferredOrder.new_logical_cmp_half_overload_map()

        overload_map |= BinaryOpDeferredOrder.new_float_arithmetic_half_overload_map()
        overload_map |= BinaryOpDeferredOrder.new_float_comparison_half_overload_map()

        return overload_map

    @staticmethod
    def new_int_arithmetic_half_overload_map():
        return {
            (
                binary_operator,
                type.get_int_type(i, is_unsigned=is_unsigned)
            ): (
                type.get_int_type(i, is_unsigned=is_unsigned)
            )
            for i in (
                8,
                16,
                32,
                64,
                128
            )
            for is_unsigned in (
                False,
                True
            )
            for binary_operator in (
                ast.node.BinaryOp.Pow,
                ast.node.BinaryOp.Mul,
                ast.node.BinaryOp.Div,
                ast.node.BinaryOp.Rem,
                ast.node.BinaryOp.Add,
                ast.node.BinaryOp.Sub
            )
        }

    @staticmethod
    def new_int_comparison_half_overload_map():
        return {
            (
                binary_operator,
                type.get_int_type(i, is_unsigned=src_is_unsigned)
            ): (
                type.get_int_type(1, is_unsigned=True)
            )
            for i in (
                8,
                16,
                32,
                64,
                128
            )
            for src_is_unsigned in (
                False,
                True
            )
            for binary_operator in (
                ast.node.BinaryOp.LT,
                ast.node.BinaryOp.GT,
                ast.node.BinaryOp.LEq,
                ast.node.BinaryOp.GEq,
                ast.node.BinaryOp.Eq,
                ast.node.BinaryOp.NE
            )
        }

    @staticmethod
    def new_float_arithmetic_half_overload_map():
        return {
            (
                binary_operator,
                type.get_float_type(i)
            ): (
                type.get_float_type(i)
            )
            for i in (
                32,
                64
            )
            for binary_operator in (
                ast.node.BinaryOp.Pow,
                ast.node.BinaryOp.Mul,
                ast.node.BinaryOp.Div,
                ast.node.BinaryOp.Rem,
                ast.node.BinaryOp.Add,
                ast.node.BinaryOp.Sub
            )
        }

    @staticmethod
    def new_float_comparison_half_overload_map():
        return {
            (
                binary_operator,
                type.get_float_type(i)
            ): (
                type.get_int_type(1, is_unsigned=True)
            )
            for i in (
                32,
                64
            )
            for binary_operator in (
                ast.node.BinaryOp.Pow,
                ast.node.BinaryOp.Mul,
                ast.node.BinaryOp.Div,
                ast.node.BinaryOp.Rem,
                ast.node.BinaryOp.Add,
                ast.node.BinaryOp.Sub
            )
        }

    @staticmethod
    def new_logical_cmp_half_overload_map():
        return {
            (
                binary_operator,
                type.get_int_type(1, is_unsigned=True)
            ): (
                type.get_int_type(1, is_unsigned=True)
            )
            for binary_operator in (
                ast.node.BinaryOp.LogicalAnd,
                ast.node.BinaryOp.LogicalOr
            )
        }


def is_var_tid(tid):
    tk = type.kind.of(tid)
    return is_var_tk(tk)


def is_var_tk(tk):
    return tk in (
        type.kind.TK.FreeVar,
        type.kind.TK.BoundVar
    )
