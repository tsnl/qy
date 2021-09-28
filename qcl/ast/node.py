"""
The AST module provides objects to identify parts of input source code.
- verbosely named so as to not conflict with Python's builtin `ast` module, used for Python runtime reflection.
"""

import enum
import abc
import typing as t

from collections import defaultdict
from qcl.typer import definition

from qcl import excepts
from qcl import frontend
from qcl import feedback
from qcl import types
from qcl import typer


all_node_table = []


def get_node_by_index(node_index: int) -> "BaseNode":
    return all_node_table[node_index]


class BaseNode(object, metaclass=abc.ABCMeta):
    # Every node is expected to have a dataclass instance named 'DATA' on the class.
    # The below constructor services all these classes.

    def __init__(self, loc: "feedback.ILoc"):
        global all_node_table
        
        super().__init__()
        self.loc = loc
        self.index = len(all_node_table)
        all_node_table.append(self)


class TypedBaseNode(BaseNode):
    x_tid: t.Optional["types.identity.TID"]
    x_ses: t.Optional["types.side_effects.SES"]
    x_ctx: t.Optional["typer.context.Context"]

    def __init__(self, loc: "feedback.ILoc"):
        super().__init__(loc)
        self.x_tid = None       # types-ID: the value of this expression is always of this types
        self.x_ses = None       # side-effects-specifier: what capabilities does this expression need?
        self.x_ctx = None       # context: semantics of where expression is used
        self.x_rml = None       # rel memory loc: for mem-window types, handles where memory is stored.

    @property
    def tid(self) -> t.Optional["types.identity.TID"]:
        return self.x_tid

    @property
    def ses(self) -> t.Optional["types.side_effects.SES"]:
        return self.x_ses

    @property
    def ctx(self) -> t.Optional["typer.context.Context"]:
        return self.x_ctx

    @property
    def type_info_finalized(self):
        is_finalized = self.x_tid is not None
        if is_finalized:
            assert self.x_ctx is not None
        return is_finalized

    def finalize_type_info(
            self,
            tid: "types.identity.TID",
            ses: "types.side_effects.SES",
            ctx: "typer.context.Context"
    ):
        assert not self.type_info_finalized
        self.x_tid = tid
        self.x_ses = ses
        self.x_ctx = ctx


#
# Expressions used to evaluate values, types, and classes.
#

class BaseExp(TypedBaseNode, metaclass=abc.ABCMeta):
    pass


class UnitExp(BaseExp):
    pass


class NumberExp(BaseExp):
    def __init__(self, loc: "feedback.ILoc", text: str):
        super().__init__(loc)
        self.text = text

        # initializing 'base':
        if self.text.startswith("0x") or self.text.startswith("0X"):
            self.base = 16
        else:
            self.base = 10

        # initializing `digits` and `suffix`:
        # note 'digits' still may contain '0x' prefix and '_'
        if self.text[-1].isalpha():
            self.digits = self.text[:-1]
            self.suffix = self.text[-1]
        else:
            self.digits = self.text[:-1]
            self.suffix = None

        # cleaning 'self.digits' prefix:
        if self.base == 16:
            assert self.digits.startswith("0x")
            self.digits = self.digits[2:]

        # cleaning `digits`: removing all underscores
        self.digits = self.digits.replace('_', '')

        # checking coarse 'kind' based on suffix:
        unsigned_int_suffix_iterable = ('t', 'B', 'H', 'I', 'L', 'Q', 'N')
        signed_int_suffix_iterable = ('b', 'h', 'i', 'l', 'q', 'n')
        float_suffix_iterable = ('f', 'd')
        all_suffices = (
            unsigned_int_suffix_iterable +
            signed_int_suffix_iterable +
            float_suffix_iterable
        )
        assert self.suffix is None or self.suffix in all_suffices
        self.is_float = (
            self.suffix in float_suffix_iterable or
            ('.' in self.digits)
        )
        self.is_unsigned_int = (
            self.suffix in unsigned_int_suffix_iterable
        )
        self.is_signed_int = (
            self.suffix in signed_int_suffix_iterable
        ) or (
            not (self.is_float or self.is_unsigned_int)
        )
        self.is_implicitly_typed = self.suffix is None

        # setting width in bits based on suffix:
        # TODO: acquire pointer-size in bytes based on target; currently hard-coded for 64-bit.
        pointer_size_in_bytes = 8
        self.width_in_bits = {
            't': 1,
            'b': 8, 'B': 8,
            'h': 16, 'H': 16,
            'i': 32, 'I': 32,
            'l': 64, 'L': 64,
            'q': 128, 'Q': 128,
            'n': 8 * pointer_size_in_bytes, 'N': 8 * pointer_size_in_bytes,
            'e': 16, 'f': 32, 'd': 64,
            None: None
        }[self.suffix]

        # calculating value:
        if self.base == 10:
            unprefixed_text = self.text
        elif self.base == 16:
            unprefixed_text = self.text[2:]
        else:
            raise NotImplementedError("Computing 'value_text' for NumberExp of unknown base")
        self.value_text = "".join((
            c
            for c in unprefixed_text
            if c != '_' and c not in all_suffices
        ))

    def __str__(self):
        return self.text


class StringExp(BaseExp):
    def __init__(self, loc, chunks: t.List["StringExpChunk"]):
        super().__init__(loc)

        self.chunks = chunks

        self.runes = []
        self.text = ""
        for chunk in self.chunks:
            self.runes += chunk.runes
            self.text += chunk.text

    def __str__(self):
        return ' '.join(map(str, self.chunks))


class StringExpChunk(BaseExp):
    def __init__(self, loc, runes: t.List[int], quote_str: str):
        super().__init__(loc)
        self.runes = runes
        self.text = ''.join(chr(rune) for rune in self.runes)
        self.rune_count = len(self.runes)
        self.quote_str = quote_str

    def __str__(self):
        return repr(self.text)


class IdExp(BaseExp):
    name: str
    found_def_rec: t.Optional[definition.BaseRecord]

    def __init__(self, loc, name):
        super().__init__(loc)
        self.name = name
        self.found_def_rec = None

    def __str__(self):
        return self.name


class LambdaExp(BaseExp):
    def __init__(self, loc: "feedback.ILoc", arg_names: t.List[str], body: BaseExp):
        super().__init__(loc)
        self.arg_names = arg_names
        self.body = body
        self.ret_ses = types.side_effects.SES.Tot
        self.non_local_name_map = {}
        self.global_name_map = {}

    def finalize_fn_ses(self, ses: "types.side_effects.SES"):
        assert ses in (
            types.side_effects.SES.Tot,
            types.side_effects.SES.Dv,
            types.side_effects.SES.ST,
            types.side_effects.SES.Exn,
            types.side_effects.SES.ML,
        )
        self.ret_ses = ses

    def add_non_local_id_ref(self, non_local_id_name, non_local_id_def_rec):
        assert non_local_id_name not in self.non_local_name_map
        self.non_local_name_map[non_local_id_name] = non_local_id_def_rec

    def add_global_id_ref(self, name, found_def_obj):
        opt_existing_def_rec = self.global_name_map.get(name, None)
        if opt_existing_def_rec is None:
            self.global_name_map[name] = found_def_obj
        else:
            assert found_def_obj is opt_existing_def_rec


class BaseCallExp(BaseExp, metaclass=abc.ABCMeta):
    class Style(enum.Enum):
        UnaryOp = enum.auto()
        BinaryOp = enum.auto()
        PostfixVCall = enum.auto()
        PostfixTCall = enum.auto()

    def __init__(self, loc: "feedback.ILoc", style):
        super().__init__(loc)
        self.style = style


class UnaryOp(enum.Enum):
    LogicalNot = enum.auto()
    DeRef = enum.auto()
    Pos = enum.auto()
    Neg = enum.auto()


class UnaryExp(BaseCallExp):
    def __init__(self, loc: "feedback.ILoc", unary_op: UnaryOp, operand: BaseExp):
        super().__init__(loc, BaseCallExp.Style.UnaryOp)
        self.unary_op = unary_op
        self.arg_exp = operand


class BinaryOp(enum.Enum):
    Pow = enum.auto()
    Mul = enum.auto()
    Div = enum.auto()
    Rem = enum.auto()
    Add = enum.auto()
    Sub = enum.auto()
    LT = enum.auto()
    LEq = enum.auto()
    GT = enum.auto()
    GEq = enum.auto()
    Eq = enum.auto()
    NE = enum.auto()
    LogicalAnd = enum.auto()
    LogicalOr = enum.auto()


class BinaryExp(BaseCallExp):
    def __init__(self, loc: "feedback.ILoc", op: "BinaryOp", lt_arg: "BaseExp", rt_arg: "BaseExp"):
        super().__init__(loc, BaseCallExp.Style.BinaryOp)
        self.binary_op = op
        self.lt_arg_exp = lt_arg
        self.rt_arg_exp = rt_arg


#
# Postfix Calls:
#

class PostfixVCallExp(BaseCallExp):
    def __init__(self, loc: "feedback.ILoc", called: "BaseExp", arg: "BaseExp", has_se: bool):
        super().__init__(loc, BaseCallExp.Style.PostfixVCall)
        self.called_exp = called
        self.arg_exp = arg
        self.has_se = has_se


#
# Assignment:
#

class AssignExp(BaseExp):
    def __init__(self, loc, dst_exp: BaseExp, src_exp: BaseExp, is_tot: bool):
        super().__init__(loc)
        self.dst_exp = dst_exp
        self.src_exp = src_exp
        self.is_tot = is_tot


#
# If-Else:
#

class IfExp(BaseExp):
    def __init__(self, loc, cond_exp, then_exp, opt_else_exp):
        super().__init__(loc)
        self.cond_exp = cond_exp
        self.then_exp = then_exp
        self.opt_else_exp = opt_else_exp


#
# Tabular Expressions:
#

class BaseModExp(TypedBaseNode):
    module_id_counter = 0

    def __init__(self, loc):
        super().__init__(loc)
        self.module_id = self.generate_fresh_module_id()
        self.own_def_rec_from_typer = None

    @staticmethod
    def generate_fresh_module_id():
        BaseModExp.module_id_counter += 1
        return BaseModExp.module_id_counter


class FileModExp(BaseModExp):
    def __init__(
            self, loc: feedback.ILoc,
            source: frontend.FileModuleSource,
            imports_map: t.Dict[str, str], exports_list: t.List[str],
            sub_module_map: t.Dict[str, "SubModExp"]
    ):
        super().__init__(loc)
        self.source = source
        self.sub_module_map = sub_module_map
        self.imports_path_map = imports_map
        self.export_sub_module_names = exports_list

        # linking `self` back to the source:
        self.source.ast_file_mod_exp_from_frontend = self

        # creating a map for `frontend` to write to with FileModuleSource instances:
        self.imports_source_map_from_frontend = {}

    def __str__(self):
        return self.source.file_path_rel_cwd


class SubModExp(BaseModExp):
    def __init__(
            self, loc: feedback.ILoc,
            template_arg_names: t.List[str], 
            elements: t.List["BaseElem"]
    ):
        super().__init__(loc)
        self.table = Table(
            loc, "submodule",
            elements,
            accepts_binding_elements=True,
            accepts_typing_elements=True,
            accepts_imperative_elements=False
        )
        self.template_arg_names = template_arg_names
        self.template_def_list_from_typer = None
        self.bind1v_def_obj_list_from_typer = None
        self.bind1t_def_obj_list_from_typer = None
        self.mast_bind1v_field_index_mapping_from_monomorphizer = None
        self.mast_bind1t_field_index_mapping_from_monomorphizer = None


class ChainExp(BaseExp):
    def __init__(
            self, loc, elements, opt_tail: t.Optional[BaseExp],
            opt_prefix_ts: t.Optional["BaseTypeSpec"],
            opt_prefix_es: t.Optional["types.side_effects.SES"]
    ):
        """
        Creates a new chain expression.
        :param loc:
        :param elements:
        :param opt_tail:
        """

        super().__init__(loc)

        assert opt_tail is None or isinstance(opt_tail, BaseExp)
        self.opt_tail = opt_tail

        self.table = Table(
            loc, "chain-exp", elements,
            accepts_binding_elements=True,
            accepts_typing_elements=True,
            accepts_imperative_elements=True
        )

        self.opt_prefix_ts = opt_prefix_ts
        self.opt_prefix_es = opt_prefix_es


class CastExp(BaseExp):
    def __init__(self, loc, constructor_ts: "BaseTypeSpec", initializer_data: "BaseExp"):
        super().__init__(loc)
        self.constructor_ts = constructor_ts
        self.initializer_data = initializer_data


#
# Tuples:
#

class TupleExp(BaseExp):
    items: t.List[BaseExp]

    def __init__(self, loc, items: t.List[BaseExp]):
        super().__init__(loc)
        self.items = items


#
#
# Type specs evaluate to types at compile-time.
#
#

class BaseTypeSpec(TypedBaseNode):
    pass


class UnitTypeSpec(BaseTypeSpec):
    pass


class IdTypeSpec(BaseTypeSpec):
    name: str
    found_def_rec: t.Optional[definition.BaseRecord]

    def __init__(self, loc: "feedback.ILoc", name: str):
        super().__init__(loc)
        self.name = name
        self.found_def_rec = None

    def __str__(self):
        return self.name


class IdTypeSpecInModule(BaseTypeSpec):
    data: "IdNodeInModuleHelper"

    def __init__(
            self,
            loc: "feedback.ILoc",
            opt_container: t.Optional["GetModuleNode"],
            elem_name: str,
            elem_args=None
    ):
        super().__init__(loc)
        opt_container_data = None if opt_container is None else opt_container.data
        self.data = IdNodeInModuleHelper(loc, opt_container_data, elem_name, elem_args)

    def __str__(self):
        return str(self.data)


class TupleTypeSpec(BaseTypeSpec):
    items: t.List[BaseTypeSpec]

    def __init__(self, loc: "feedback.ILoc", items: t.List[BaseTypeSpec]):
        super().__init__(loc)
        self.items = items


class FnSignatureTypeSpec(BaseTypeSpec):
    arg_type_spec: BaseTypeSpec
    return_type_spec: BaseTypeSpec
    opt_ses: t.Optional["types.side_effects.SES"]

    def __init__(self, loc, arg_type_spec, return_type_spec, opt_ses):
        super().__init__(loc)
        self.arg_type_spec = arg_type_spec
        self.return_type_spec = return_type_spec
        self.opt_ses = opt_ses


class BaseMemWindowTypeSpec(BaseTypeSpec, metaclass=abc.ABCMeta):
    is_mut: bool

    def __init__(self, loc: "feedback.ILoc", is_mut: bool):
        super().__init__(loc)
        self.is_mut = is_mut


class PtrTypeSpec(BaseMemWindowTypeSpec):
    ptd_ts: BaseTypeSpec

    def __init__(self, loc, is_mut, pointee_type_spec):
        super().__init__(loc, is_mut)
        self.ptd_ts = pointee_type_spec


class ArrayTypeSpec(BaseMemWindowTypeSpec):
    elem_ts: BaseTypeSpec
    array_count: BaseExp

    def __init__(self, loc: "feedback.ILoc", is_mut: bool, elem_type_spec: BaseTypeSpec, array_count: BaseExp):
        super().__init__(loc, is_mut)
        self.elem_ts = elem_type_spec
        self.array_count = array_count


class SliceTypeSpec(BaseMemWindowTypeSpec):
    elem_ts: BaseTypeSpec

    def __init__(self, loc: "feedback.ILoc", is_mut: bool, elem_type_spec: BaseTypeSpec):
        super().__init__(loc, is_mut)
        self.elem_ts = elem_type_spec


class AdtKind(enum.Enum):
    Structure = enum.auto()


class AdtTypeSpec(BaseTypeSpec):
    def __init__(self, adt_kind, loc, elements):
        super().__init__(loc)
        self.adt_kind = adt_kind

        self.alias = {
            AdtKind.Structure: "struct"
        }[self.adt_kind]
        self.table = Table(
            self.loc, self.alias, elements,
            accepts_typing_elements=True,
            accepts_binding_elements=False,
            accepts_imperative_elements=False
        )


#
# AllocateExp
#


class Allocator(enum.Enum):
    Stack = enum.auto()
    Heap = enum.auto()


class BaseAllocateExp(BaseExp, metaclass=abc.ABCMeta):
    def __init__(self, allocator: Allocator, is_mut: bool, loc: feedback.ILoc):
        super().__init__(loc)
        self.allocator = allocator
        self.is_mut = is_mut


class AllocatePtrExp(BaseAllocateExp):
    def __init__(self, allocator: Allocator, is_mut: bool, loc, initializer_exp):
        super().__init__(allocator, is_mut, loc)
        self.initializer_exp = initializer_exp


class AllocateArrayExp(BaseAllocateExp):
    def __init__(
            self,
            allocator: Allocator, is_mut: bool,
            loc: feedback.ILoc,
            collection_ts: "BaseTypeSpec",
            array_size_exp: BaseExp, opt_initializer_exp: t.Optional[BaseExp]
    ):
        super().__init__(allocator, is_mut, loc)
        self.array_size_exp = array_size_exp
        self.opt_initializer_exp = opt_initializer_exp
        self.collection_ts = collection_ts


class AllocateSliceExp(BaseAllocateExp):
    def __init__(
            self,
            allocator: Allocator, is_mut: bool,
            loc: feedback.ILoc,
            collection_ts: "BaseTypeSpec",
            opt_initializer_exp: BaseExp
    ):
        super().__init__(allocator, is_mut, loc)
        self.opt_initializer_exp = opt_initializer_exp
        self.collection_ts = collection_ts


#
#
# Tables & Elements:
#
#

class Table(object):
    """
    Tables represent associative data, and are used for structs, modules, and chains.
    They are composed of elements with unique string names and an order of initialization.
    Table instances are encapsulated rather than inherited from.
    Table does not need to be subclassed-- it is parametrically controlled.
    """

    def __init__(
            self, loc, alias: str, elements: t.List["BaseElem"],
            accepts_binding_elements=True,
            accepts_typing_elements=True,
            accepts_imperative_elements=False,
            import_sym_names: t.Optional[t.Iterable[str]] = None
    ):
        super().__init__()
        self.loc = loc
        self.alias = alias

        # we store a list of all elements:
        self.elements = elements

        # parsing stores a map of ID names to concerned elements:
        self.binding_elems_map = defaultdict(list)
        self.typing_elems_map = defaultdict(list)

        # parsing stores an ordered list of things to do, or specification about
        # the context where these things are done:
        self.ordered_type_bind_elems = []
        self.ordered_value_imp_bind_elems = []
        self.ordered_typing_elems = []

        # toggles for accepting different statement kinds:
        # - enforced during validation, not parsing
        self.accepts_binding_elems = accepts_binding_elements
        self.accepts_typing_elems = accepts_typing_elements
        self.accepts_imperative_elems = accepts_imperative_elements

        # storing any extra symbols (e.g. import, template params):
        self.extra_sym_names = import_sym_names

        #
        # Parsing / Validating:
        #

        # first, injecting all 'extra_symbols' provided to the constructor:
        # - used for import, template args
        # - defining here lets us naturally detect conflicts at only one point, while parsing
        if import_sym_names is not None:
            for extra_sym_name in import_sym_names:
                self.binding_elems_map[extra_sym_name].append('<internal-def>')

        # parsing all elements:
        # override 'parse' methods to update above fields & others.
        self.table_parsed_ok = self.parse_all_elements()

        # validating parsed data:
        self.table_validated_ok = self.validate_parsed_data()

        # summary `ok` property:
        self.ok = (
                self.table_parsed_ok and
                self.table_validated_ok
        )

    def parse_all_elements(self):
        parse_ok = all(map(self.parse_element, self.elements))
        return parse_ok

    def parse_element(self, element):
        if isinstance(element, BaseBindElem):
            return self.parse_binding_elem(element)

        elif isinstance(element, BaseTypingElem):
            return self.parse_typing_elem(element)

        elif isinstance(element, BaseImperativeElem):
            return self.parse_imperative_elem(element)

        # Failure cases:
        elif element is None:
            assert False and "'None' element parsed-- is this an ANTLRVisitor error?"
        else:
            raise NotImplementedError("Unknown types of `element` instance.")

    def parse_binding_elem(self, elem: "BaseBindElem"):
        if isinstance(elem, Bind1VElem):
            self.ordered_value_imp_bind_elems.append(elem)
        elif isinstance(elem, Bind1TElem):
            self.ordered_type_bind_elems.append(elem)
        else:
            assert "Unknown binding 'elem' subclass" and False

        self.binding_elems_map[elem.id_name].append(elem)
        return True

    def parse_typing_elem(self, elem: "BaseTypingElem"):
        self.ordered_typing_elems.append(elem)
        self.typing_elems_map[elem.id_name].append(elem)
        return True

    def parse_imperative_elem(self, elem: "BaseImperativeElem"):
        self.ordered_value_imp_bind_elems.append(elem)
        return self.accepts_imperative_elems

    def validate_parsed_data(self):
        # performs additional validation after parsing, e.g.
        # - if invalid elements in this table
        # - if multiple symbols bound in the same table
        # - if any bindings conflict with template params

        ok = True

        # ensuring each element types is accepted:
        for element in self.elements:
            if isinstance(element, BaseBindElem):
                if not self.accepts_binding_elems:
                    msg_suffix = f"binding element not permitted table at {element.loc}"
                    raise excepts.ParserCompilationError(msg_suffix)
            elif isinstance(element, BaseTypingElem):
                if not self.accepts_typing_elems:
                    msg_suffix = f"typing element not permitted in table: {element.loc}"
                    raise excepts.ParserCompilationError(msg_suffix)
            elif isinstance(element, BaseImperativeElem):
                if not self.accepts_imperative_elems:
                    msg_suffix = f"imperative element not permitted in table: {element.loc}"
                    raise excepts.ParserCompilationError(msg_suffix)

        return ok


# Elements are of 3 broad types:
# - typing elements
# - binding elements
# - imperative elements: the 'do' element

class ElementKind(enum.Enum):
    # Typing elements:
    TypingValueID = enum.auto()
    TypingTypeID = enum.auto()
    TypingClassID = enum.auto()

    # Binding elements:
    BindOneValueID = enum.auto()
    BindOneTypeID = enum.auto()
    BindOneClassID = enum.auto()

    # Imperative elements:
    Do = enum.auto()


class BaseElem(BaseNode):
    element_kind: ElementKind


# Typing elements:
# used to specify the types of any bound element in this table.

class BaseTypingElem(BaseElem):
    id_name: str

    def __init__(self, loc, id_name: str):
        super().__init__(loc)
        self.id_name = id_name


class Type1VElem(BaseTypingElem):
    type_spec: "BaseTypeSpec"

    def __init__(self, loc, id_name, type_spec: "BaseTypeSpec"):
        super().__init__(loc, id_name)
        self.type_spec = type_spec


# Binding elements:
# used to bind a new variable while providing minimal types information.

class BaseBindElem(BaseElem):
    def __init__(self, loc, id_name):
        super().__init__(loc)
        self.id_name = id_name


class Bind1VElem(BaseBindElem):
    bound_exp: "BaseExp"

    def __init__(self, loc, id_name: str, exp: "BaseExp"):
        super().__init__(loc, id_name)
        self.bound_exp = exp


class Bind1TElem(BaseBindElem):
    id_name: str
    bound_type_spec: "BaseTypeSpec"

    def __init__(self, loc, id_name: str, type_spec: "BaseTypeSpec"):
        assert type_spec is not None

        super().__init__(loc, id_name)
        self.bound_type_spec = type_spec


class BaseImperativeElem(BaseElem, metaclass=abc.ABCMeta):
    pass


class ForceEvalElem(BaseImperativeElem):
    discarded_exp: BaseExp

    def __init__(self, loc, discarded_exp):
        super().__init__(loc)
        self.discarded_exp = discarded_exp


#
# GetModElement expressions:
#

class IdExpInModule(BaseExp):
    data: "IdNodeInModuleHelper"

    def __init__(
            self,
            loc, opt_container: "GetModuleNode",
            elem_name: str,
            elem_args=None,
    ):
        super().__init__(loc)
        opt_container_data = None if opt_container is None else opt_container.data
        self.data = IdNodeInModuleHelper(loc, opt_container_data, elem_name, elem_args=elem_args)

    def __str__(self):
        return str(self.data)


#
# GetElementByDot expressions:
#

class GetElementByDotNameExp(BaseExp):
    container: BaseExp
    key_name: str

    def __init__(self, loc, container, key_name):
        super().__init__(loc)
        self.container = container
        self.key_name = key_name


class GetElementByDotIndexExp(BaseExp):
    container: BaseExp
    index: BaseExp
    index_wrapped_by_parens: bool

    def __init__(self, loc, container, index, index_wrapped_by_parens):
        super().__init__(loc)
        self.container = container
        self.index = index
        self.index_wrapped_by_parens = index_wrapped_by_parens


#
# TODO: add/amend AST nodes for pointers, arrays, and slice literals.
#


class IdNodeInModuleHelper(object):
    opt_container: t.Optional["IdNodeInModuleHelper"]
    elem_args: t.List[t.Union[BaseExp, BaseTypeSpec]]
    elem_name: str
    opt_child: t.Optional["IdNodeInModuleHelper"]
    found_def_rec: t.Optional["typer.definition.BaseRecord"]
    instantiate_sub: t.Optional["typer.substitution.Substitution"]

    def __init__(self, loc, opt_container, elem_name, elem_args=None):
        super().__init__()
        self.loc = loc
        self.opt_container = opt_container
        self.elem_name = elem_name
        self.opt_child = None
        self.found_def_rec = None
        self.instantiate_sub = None

        if elem_args is not None:
            self.elem_args = elem_args
        else:
            self.elem_args = []

        if self.opt_container is not None:
            self.opt_container.opt_child = self

    @property
    def has_child(self):
        return self.opt_child is not None

    def __str__(self):
        if self.elem_args:
            elem_args_str = f"[{','.join(map(str, self.elem_args))}]"
        else:
            elem_args_str = ""

        if self.opt_container is not None:
            return f"{self.opt_container}:{self.elem_name}{elem_args_str}"
        else:
            return f"{self.elem_name}{elem_args_str}"


#
# GetModuleNode: a name-reference to a defined/imported module with optional template arguments.
#

class GetModuleNode(BaseNode):
    data: "IdNodeInModuleHelper"

    def __init__(
            self,
            loc: feedback.ILoc,
            opt_container: t.Optional["GetModuleNode"],
            elem_name: str,
            elem_args=None
    ):
        super().__init__(loc)
        opt_container_data = None if opt_container is None else opt_container.data
        self.data = IdNodeInModuleHelper(loc, opt_container_data, elem_name, elem_args=elem_args)
