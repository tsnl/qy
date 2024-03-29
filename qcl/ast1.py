"""
`ast1` represents the contents of a single Qy source file.
"""

import abc
import typing as t
import enum
from collections import defaultdict

from . import common
from . import feedback as fb

if t.TYPE_CHECKING:
    from . import typer

#
#
# Helpers:
#
#

OptStr = t.Optional[str]


#
#
# Constants:
#
#

class UnaryOperator(enum.Enum):
    DeRef = enum.auto()
    LogicalNot = enum.auto()
    Minus = enum.auto()
    Plus = enum.auto()
    Do = enum.auto()        # applies a thunk


class BinaryOperator(enum.Enum):
    Mul = enum.auto()
    Div = enum.auto()
    Mod = enum.auto()
    Add = enum.auto()
    Sub = enum.auto()
    LSh = enum.auto()
    RSh = enum.auto()
    LThan = enum.auto()
    GThan = enum.auto()
    LEq = enum.auto()
    GEq = enum.auto()
    Eq = enum.auto()
    NEq = enum.auto()
    BitwiseAnd = enum.auto()
    BitwiseXOr = enum.auto()
    BitwiseOr = enum.auto()
    LogicalAnd = enum.auto()
    LogicalOr = enum.auto()


class BuiltinPrimitiveTypeIdentity(enum.Enum):
    Float32 = enum.auto()
    Float64 = enum.auto()
    Float128 = enum.auto()
    Int64 = enum.auto()
    Int32 = enum.auto()
    Int16 = enum.auto()
    Int8 = enum.auto()
    UInt64 = enum.auto()
    UInt32 = enum.auto()
    UInt16 = enum.auto()
    UInt8 = enum.auto()
    Bool = enum.auto()
    Void = enum.auto()


class LinearTypeOp(enum.Enum):
    Product = enum.auto()
    Sum = enum.auto()


#
#
# Base classes and mixins:
#
#

class BaseFileNode(object, metaclass=abc.ABCMeta):
    def __init__(self, loc: fb.ILoc):
        super().__init__()
        self.loc = loc
        self.wb_ctx = None

    @property
    def desc(self):
        return self.__class__.__name__


class WbTypeMixin(common.Mixin):
    all = []

    # sub_index is an index of free variables to expressions in which they occur.
    # it is updated and used by 'apply_sub_everywhere'
    sub_index = defaultdict(list)
    
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._wb_type = None

        WbTypeMixin.all.append(self)
        
    @property
    def wb_type(self):
        return self._wb_type
    
    @wb_type.setter
    def wb_type(self, new_type):
        self._wb_type = new_type
        WbTypeMixin.index_ast_node(WbTypeMixin.sub_index, self)

    @staticmethod
    def index_ast_node(new_index, ast_node):
        assert ast_node._wb_type is not None
        for t in ast_node._wb_type.oc_free_vars:
            new_index[t].append(ast_node)

    @staticmethod
    def apply_sub_everywhere(sub):
        new_index = defaultdict(list)
        
        for ast_node in WbTypeMixin.all:
            if ast_node._wb_type is not None:
                ast_node._wb_type = sub.rewrite_type(ast_node._wb_type)
                WbTypeMixin.index_ast_node(new_index, ast_node)

        WbTypeMixin.sub_index = new_index


class BaseTypeSpec(WbTypeMixin, BaseFileNode):
    def __init__(self, loc: fb.ILoc):
        super().__init__(loc)


class BaseExpression(WbTypeMixin, BaseFileNode):
    def __init__(self, loc: fb.ILoc):
        super().__init__(loc)
        self.opt_cached_const_value = None
        self.cache_valid = False


class BaseStatement(BaseFileNode):
    def __init__(self, loc: fb.ILoc):
        super().__init__(loc)


class MIdQualifierNode(common.Mixin):
    def __init__(self, name: str, *args, **kwargs) -> None:
        assert isinstance(self, BaseFileNode)
        super().__init__(*args, **kwargs)
        self.name = name

    def lookup_def_obj(self):
        assert self.wb_ctx is not None
        res = self.wb_ctx.try_lookup(self.name)
        assert res is not None
        return res



#
#
# Statements:
#
#

class BaseIdQualifierStatement(MIdQualifierNode, BaseStatement):
    def __init__(self, loc: fb.ILoc, name: str):
        super().__init__(name, loc)


class Bind1vStatement(BaseIdQualifierStatement):
    def __init__(self, loc: fb.ILoc, name: str, initializer: t.Optional[BaseExpression], is_constant: bool = False):
        super().__init__(loc, name)
        self.initializer = initializer
        self.is_constant = is_constant


class Bind1fStatement(BaseIdQualifierStatement):
    def __init__(
        self, 
        loc: fb.ILoc, 
        name: str, 
        arg_names: t.List[str], arg_types: t.List["BaseTypeSpec"], 
        body: t.Optional["BaseExpression"], opt_ret_ts: t.Optional["BaseTypeSpec"], 
        is_variadic: bool = False,
        is_pub: bool = False
    ):
        assert isinstance(body, (type(None), BaseExpression))
        super().__init__(loc, name)
        self.args_names = arg_names
        self.args_types = arg_types
        self.body_exp = body
        self.opt_ret_ts = opt_ret_ts
        self.is_variadic = is_variadic
        self.is_pub = is_pub
        self.x_def: t.Optional["typer.BaseDefinition"] = None

    def is_extern(self):
        if isinstance(self, Bind1fStatement):
            assert self.body_exp is None
            return True
        else:
            return False


class Extern1vStatement(Bind1vStatement):
    def __init__(self, loc, var_name: str, var_ts: "BaseTypeSpec", var_str):
        super().__init__(loc, var_name, None)
        self.var_type_spec = var_ts
        self.extern_notation = var_str

    def __str__(self) -> str:
        return self.extern_notation


class Extern1fStatement(Bind1fStatement):
    def __init__(
        self, loc: fb.ILoc, 
        name: str, arg_names: t.List[str], arg_typespecs: t.List["BaseTypeSpec"], ret_typespec: "BaseTypeSpec",
        extern_notation: str
    ):
        super().__init__(loc, name, arg_names, arg_typespecs, None, ret_typespec)
        self.extern_notation = extern_notation
    
    def __str__(self) -> str:
        return self.extern_notation
        


class Bind1tStatement(BaseIdQualifierStatement):
    def __init__(self, loc: fb.ILoc, name: str, initializer: BaseTypeSpec):
        super().__init__(loc, name)
        self.initializer = initializer


class ConstStatement(BaseStatement):
    def __init__(self, loc: fb.ILoc, body: t.List[BaseStatement], const_type_spec: "BaseTypeSpec"):
        super().__init__(loc)
        self.loc = loc
        self.body = body
        self.const_type_spec = const_type_spec
        self.wb_ctx_chain = []
        self.wb_synth_pred_binders = []

    @property
    def root_ctx(self):
        return self.wb_ctx_chain[0]

    def pre_ctx_of_constant(self, i):
        return self.wb_ctx_chain[i]
    
    def post_ctx_of_constant(self, i):
        return self.wb_ctx_chain[i+1]


class ReturnStatement(BaseStatement):
    def __init__(self, loc, returned_exp: BaseExpression, is_shallow=True):
        super().__init__(loc)
        self.returned_exp = returned_exp
        self.is_shallow = is_shallow


class DiscardStatement(BaseStatement):
    def __init__(self, loc: fb.ILoc, discarded_exp: BaseExpression):
        super().__init__(loc)
        self.discarded_exp = discarded_exp


class LoopStyle(enum.Enum):
    WhileDo = enum.auto()
    DoWhile = enum.auto()


class LoopStatement(BaseStatement):
    def __init__(self, loc: fb.ILoc, cond: BaseExpression, body: BaseExpression, loop_style: LoopStyle):
        super().__init__(loc)
        self.cond = cond
        self.body = body
        self.loop_style = loop_style


#
#
# Expressions:
#
#

class BaseNumberExpression(BaseExpression):
    def __init__(self, loc: fb.ILoc, text: str, value: t.Union[int, float], width_in_bits: int):
        super().__init__(loc)
        self.text = text
        self.value = value
        self.width_in_bits = width_in_bits


class IntExpression(BaseNumberExpression):
    def __init__(
            self,
            loc: fb.ILoc,
            text: str,
            value: int,
            base: int,
            is_unsigned: bool,
            width_in_bits: int = 32
    ):
        super().__init__(loc, text, value, width_in_bits)
        self.value: int
        self.text_base = base
        self.is_unsigned = is_unsigned
        # print("IntExpression:", self.text)


class FloatExpression(BaseNumberExpression):
    def __init__(self, loc: fb.ILoc, text: str, value: float, width_in_bits=64):
        super().__init__(loc, text, value, width_in_bits)
        self.value: float
        # print("FloatExpression:", self.text)


class StringExpression(BaseExpression):
    def __init__(self, loc: fb.ILoc, pieces: t.List[str], value: str):
        super().__init__(loc)
        self.pieces = pieces
        self.value = value
        # print("StringExpression:", self.pieces, repr(self.value))


class IdRefExpression(MIdQualifierNode, BaseExpression):
    def __init__(self, loc: fb.ILoc, name: str):
        super().__init__(name, loc)


class IfExpression(BaseExpression):
    def __init__(
        self, 
        loc: fb.ILoc, 
        cond_exp: "BaseExpression", 
        then_exp: "BaseExpression", 
        opt_else_exp: t.Optional["BaseExpression"]
    ):
        super().__init__(loc)
        self.cond_exp = cond_exp
        self.then_exp = then_exp
        self.else_exp = opt_else_exp


class LambdaExpression(BaseExpression):
    def __init__(
        self, loc: fb.ILoc, 
        opt_arg_names: t.Optional[t.List[str]],
        body_prefix: t.List["BaseExpression"],
        opt_body_tail: t.Optional["BaseExpression"],
        no_closure: bool
    ):
        super().__init__(loc)
        self.arg_names = opt_arg_names if opt_arg_names is not None else []
        self.body_prefix = body_prefix
        self.opt_body_tail = opt_body_tail
        self.no_closure = no_closure


class ProcCallExpression(BaseExpression):
    def __init__(self, loc: fb.ILoc, proc: BaseExpression, arg_exps: t.List[BaseExpression]):
        super().__init__(loc)
        self.proc = proc
        self.arg_exps = arg_exps


class ConstructExpression(BaseExpression):
    """
    Constructs an expression's value, implicitly placing constructed expression on the stack.
    Returns the value de-referencing this stack pointer.
    """

    def __init__(self, loc: fb.ILoc, made_ts: BaseTypeSpec, initializer_list: t.List[BaseExpression]):
        super().__init__(loc)
        self.made_ts = made_ts
        self.initializer_list = initializer_list
    

class CopyExpression(BaseExpression):
    """
    Allocates memory, then copies a value to this memory. Returns the pointer to memory.
    """

    class Allocator(enum.Enum):
        Push = enum.auto()  # allocates object on the stack, returns [possibly mutable] pointer
        Heap = enum.auto()  # allocates object on the stack, returns [possibly mutable] pointer
    
    def __init__(self, loc: fb.ILoc, copied_val: BaseExpression, allocator: Allocator, is_mut: bool):
        super().__init__(loc)
        self.copied_val = copied_val
        self.allocator = allocator
        self.is_mut = is_mut


class DotIdExpression(BaseExpression):
    def __init__(self, loc: fb.ILoc, container: BaseExpression, key: str):
        super().__init__(loc)
        self.container = container
        self.key = key


class IndexExpression(BaseExpression):
    def __init__(self, loc: fb.ILoc, container: BaseExpression, index: BaseExpression, ret_ref: bool):
        super().__init__(loc)
        self.container = container
        self.index = index
        self.ret_ref = ret_ref


class UnaryOpExpression(BaseExpression):
    def __init__(self, loc: fb.ILoc, operator: UnaryOperator, operand: BaseExpression):
        super().__init__(loc)
        self.operator = operator
        self.operand = operand


class BinaryOpExpression(BaseExpression):
    def __init__(self, loc: fb.ILoc, operator: BinaryOperator, lt_operand: BaseExpression, rt_operand: BaseExpression):
        super().__init__(loc)
        self.operator = operator
        self.lt_operand_exp = lt_operand
        self.rt_operand_exp = rt_operand

class UpdateExpression(BaseExpression):
    def __init__(self, loc: fb.ILoc, store_address: BaseExpression, stored_value: BaseExpression):
        super().__init__(loc)
        self.store_address = store_address
        self.stored_value = stored_value


#
#
# Type specifiers:
#
#

class IdRefTypeSpec(MIdQualifierNode, BaseTypeSpec):
    def __init__(self, loc: fb.ILoc, name: str):
        super().__init__(name, loc)


class BuiltinPrimitiveTypeSpec(BaseTypeSpec):
    def __init__(self, loc: fb.ILoc, identity: BuiltinPrimitiveTypeIdentity):
        super().__init__(loc)
        self.identity = identity

    @property
    def is_unsigned_int(self) -> bool:
        return self.identity in {
            BuiltinPrimitiveTypeIdentity.UInt8,
            BuiltinPrimitiveTypeIdentity.UInt16,
            BuiltinPrimitiveTypeIdentity.UInt32,
            BuiltinPrimitiveTypeIdentity.UInt64
        }

    @property
    def int_width_in_bits(self) -> t.Optional[int]:
        return {
            BuiltinPrimitiveTypeIdentity.Int8: 8,
            BuiltinPrimitiveTypeIdentity.Int16: 16,
            BuiltinPrimitiveTypeIdentity.Int32: 32,
            BuiltinPrimitiveTypeIdentity.Int64: 64,
            BuiltinPrimitiveTypeIdentity.UInt8: 8,
            BuiltinPrimitiveTypeIdentity.UInt16: 16,
            BuiltinPrimitiveTypeIdentity.UInt32: 32,
            BuiltinPrimitiveTypeIdentity.UInt64: 64
        }.get(self.identity, None)


class AdtTypeSpec(BaseTypeSpec):
    def __init__(self, loc: fb.ILoc, linear_op: LinearTypeOp, args: t.List[t.Tuple[OptStr, BaseTypeSpec]]):
        super().__init__(loc)
        self.linear_op = linear_op
        self.fields_list = args
        self.fields_dict = {
            arg_pair[0]: arg_pair[1]
            for arg_pair in args
            if arg_pair[0] is not None
        }

    def push_field(self, field_key):
        assert isinstance(field_key, tuple)
        assert len(field_key) == 2
        field_name, field_ts = field_key
        assert isinstance(field_name, (type(None), str))
        assert isinstance(field_ts, BaseTypeSpec)
        assert field_name not in self.fields_dict
        self.fields_list.append(field_key)
        self.fields_dict[field_name] = field_ts



class PtrTypeSpec(BaseTypeSpec):
    def __init__(self, loc: fb.ILoc, pointee_type_spec: BaseTypeSpec, is_mut: bool):
        super().__init__(loc)
        self.pointee_type_spec = pointee_type_spec
        self.is_mut = is_mut


class ArrayTypeSpec(BaseTypeSpec):
    def __init__(self, loc: fb.ILoc, element_type_spec: BaseTypeSpec, count_expression: BaseExpression, is_mut: bool):
        super().__init__(loc)
        self.element_type_spec = element_type_spec
        self.count_expression = count_expression
        self.is_mut = is_mut


class ArrayBoxTypeSpec(BaseTypeSpec):
    def __init__(self, loc: fb.ILoc, element_type_spec: BaseTypeSpec, is_mut: bool):
        super().__init__(loc)
        self.element_type_spec = element_type_spec
        self.is_mut = is_mut


class ProcSignatureTypeSpec(BaseTypeSpec):
    def __init__(
        self, 
        loc: fb.ILoc, 
        opt_args: t.Optional[t.List[t.Tuple[OptStr, BaseTypeSpec]]], 
        ret_ts: BaseTypeSpec,
        takes_closure: bool,
        is_c_variadic: bool
    ):
        super().__init__(loc)
        self.opt_args_list = opt_args
        self.ret_ts = ret_ts
        self.takes_closure = takes_closure
        self.is_c_variadic = is_c_variadic
