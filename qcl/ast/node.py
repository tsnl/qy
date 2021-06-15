"""
The AST module provides objects to identify parts of input source code.
- verbosely named so as to not conflict with Python's builtin `ast` module, used for Python runtime reflection.
"""

import enum
import abc

from collections import defaultdict
from typing import *

from qcl import feedback
from qcl import type


class BaseNode(object, metaclass=abc.ABCMeta):
    # Every node is expected to have a dataclass instance named 'DATA' on the class.
    # The below constructor services all these classes.

    def __init__(self, loc: "feedback.ILoc"):
        super().__init__()
        self.loc = loc


#
# Expressions used to evaluate values, types, and classes.
#

class BaseExp(BaseNode, metaclass=abc.ABCMeta):
    x_typeof_tid: Optional[type.identity.TID]

    def __init__(self, loc: "feedback.ILoc"):
        super().__init__(loc)
        self.x_typeof_tid = None


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
        assert self.suffix is None or self.suffix in 'fFbBuUiI'
        self.is_explicitly_float = (self.suffix in ('f', 'F')) or ('.' in self.digits)
        self.is_explicitly_unsigned = self.suffix in ('b', 'B', 'u', 'U')
        self.is_explicitly_signed = self.suffix in ('i', 'I') or (
                not self.is_explicitly_float and
                not self.is_explicitly_unsigned
        )
        self.is_implicitly_typed = self.suffix is None

        # setting width in bits based on suffix:
        self.width_in_bits = {
            'f': 32, 'F': 64,
            'b': 1, 'B': 8, 'u': 32, 'U': 64,
            'i': 32, 'I': 64,
            None: None
        }[self.suffix]


class StringExp(BaseExp):
    def __init__(self, loc, chunks: List["StringExpChunk"]):
        super().__init__(loc)

        self.chunks = chunks

        self.runes = []
        self.text = ""
        for chunk in self.chunks:
            self.runes += chunk.runes
            self.text += chunk.text


class StringExpChunk(BaseExp):
    def __init__(self, loc, runes: List[int], quote_str: str):
        super().__init__(loc)
        self.runes = runes
        self.text = ''.join(chr(rune) for rune in self.runes)
        self.rune_count = len(self.runes)
        self.quote_str = quote_str


class IdExp(BaseExp):
    name: str

    def __init__(self, loc, name):
        super().__init__(loc)
        self.name = name

        self.x_found_def = None


class LambdaExp(BaseExp):
    def __init__(self, loc: "feedback.ILoc", arg_names: List[str], body: BaseExp):
        super().__init__(loc)
        self.arg_names = arg_names
        self.body = body


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
    GetMutableRef = enum.auto()
    GetImmutableRef = enum.auto()
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
    def __init__(self, loc, dst_exp: BaseExp, src_exp: BaseExp):
        super().__init__(loc)
        self.dst_exp = dst_exp
        self.src_exp = src_exp


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

class BaseModuleExp(BaseNode):
    module_id_counter = 0

    def __init__(self, loc, template_arg_names: List[str]):
        super().__init__(loc)
        self.module_id = self.generate_fresh_module_id()
        self.template_arg_names = template_arg_names

    @staticmethod
    def generate_fresh_module_id():
        BaseModuleExp.module_id_counter += 1
        return BaseModuleExp.module_id_counter


class FileModuleExp(BaseModuleExp):
    def __init__(
            self, loc: feedback.ILoc,
            imports_map: Dict[str, str], exports_list: List[str],
            sub_module_map: Dict[str, "SubModuleExp"]
    ):
        super().__init__(loc, template_arg_names=[])
        self.sub_module_map = sub_module_map
        self.import_map = imports_map
        self.export_sub_module_names = exports_list


class SubModuleExp(BaseModuleExp):
    def __init__(
            self, loc: feedback.ILoc,
            template_arg_names: List[str], elements: List["BaseElement"]
    ):
        super().__init__(loc, template_arg_names)
        self.table = Table(
            loc, "submodule",
            elements,
            accepts_binding_elements=True,
            accepts_typing_elements=True,
            accepts_imperative_elements=False
        )


class ChainExp(BaseExp):
    def __init__(
            self, loc, elements, opt_tail: Optional[BaseExp],
            opt_prefix_ts: Optional["BaseTypeSpec"],
            opt_prefix_es: Optional[type.side_effects.SES]
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
    def __init__(self, loc, constructor_ts: "BaseTypeSpec", data: "BaseExp"):
        super().__init__(loc)
        self.constructor_ts = constructor_ts
        self.data = data


#
# Tuples:
#

class TupleExp(BaseExp):
    items: List[BaseExp]

    def __init__(self, loc, items: List[BaseExp]):
        super().__init__(loc)
        self.items = items


#
#
# Type specs evaluate to types at compile-time.
#
#

class BaseTypeSpec(BaseNode):
    is_mutable: bool

    def __init__(self, loc):
        super().__init__(loc)

        # if `is_mutable` is true, the denoted type is of the form `mut T`
        self.is_mutable = False


class SelfTypeSpec(BaseTypeSpec):
    pass


class UnitTypeSpec(BaseTypeSpec):
    pass


class IdTypeSpec(BaseTypeSpec):
    name: str

    def __init__(self, loc: "feedback.ILoc", name: str):
        super().__init__(loc)
        self.name = name

        self.x_found_def = None


class TupleTypeSpec(BaseTypeSpec):
    items: List[BaseTypeSpec]

    def __init__(self, loc: "feedback.ILoc", items: List[BaseTypeSpec]):
        super().__init__(loc)
        self.items = items


class FnSignatureTypeSpec(BaseTypeSpec):
    arg_type_spec: BaseTypeSpec
    return_type_spec: BaseTypeSpec

    def __init__(self, loc, arg_type_spec, return_type_spec):
        super().__init__(loc)
        self.arg_type_spec = arg_type_spec
        self.return_type_spec = return_type_spec


class PtrTypeSpec(BaseTypeSpec):
    pointee_type_spec: BaseTypeSpec

    def __init__(self, loc, pointee_type_spec):
        super().__init__(loc)
        self.pointee_type_spec = pointee_type_spec


class AdtKind(enum.Enum):
    TaggedUnion = enum.auto()
    UntaggedUnion = enum.auto()
    Structure = enum.auto()


class AdtTypeSpec(BaseTypeSpec):
    def __init__(self, adt_kind, loc, elements):
        super().__init__(loc)
        self.adt_kind = adt_kind

        self.alias = {
            AdtKind.TaggedUnion: "enum",
            AdtKind.UntaggedUnion: "union",
            AdtKind.Structure: "struct"
        }[self.adt_kind]
        self.table = Table(
            self.loc, self.alias, elements,
            accepts_typing_elements=True,
            accepts_binding_elements=False,
            accepts_imperative_elements=False
        )


class InterfaceTypeSpec(BaseTypeSpec):
    def __init__(self, loc, requires_elements, provides_elements):
        super().__init__(loc)
        self.requires_table = Table(
            self.loc, f"interface-requires", requires_elements,
            accepts_typing_elements=True,
            accepts_binding_elements=False,
            accepts_imperative_elements=False
        )
        self.provides_table = Table(
            self.loc, f"interface-provides", provides_elements,
            accepts_typing_elements=True,
            accepts_binding_elements=False,
            accepts_imperative_elements=False
        )


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
            self, loc, alias: str, elements: List["BaseElement"],
            accepts_binding_elements=True,
            accepts_typing_elements=True,
            accepts_imperative_elements=False,
            import_sym_names: Optional[Iterable[str]] = None
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
        self.ordered_typing_bind_elems = []
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
            assert isinstance(import_sym_names, Iterable)
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
        if isinstance(element, BaseBindElement):
            return self.parse_binding_elem(element)

        elif isinstance(element, BaseTypingElement):
            return self.parse_typing_elem(element)

        elif isinstance(element, BaseImperativeElement):
            return self.parse_imperative_elem(element)

        # Failure cases:
        elif element is None:
            assert False and "'None' element parsed-- is this an ANTLRVisitor error?"
        else:
            assert False and "Unknown element type."

    def parse_binding_elem(self, elem: "BaseBindElement"):
        if isinstance(elem, BindOneValueIDElement):
            self.ordered_value_imp_bind_elems.append(elem)
        elif isinstance(elem, BindOneTypeIDElement):
            self.ordered_typing_bind_elems.append(elem)
        else:
            assert "Unknown binding 'elem' subclass" and False

        self.binding_elems_map[elem.id_name].append(elem)
        return True

    def parse_typing_elem(self, elem: "BaseTypingElement"):
        self.ordered_typing_elems.append(elem)
        self.typing_elems_map[elem.id_name].append(elem)
        return True

    def parse_imperative_elem(self, elem: "BaseImperativeElement"):
        self.ordered_value_imp_bind_elems.append(elem)
        return self.accepts_imperative_elems

    def validate_parsed_data(self):
        # performs additional validation after parsing, e.g.
        # - if invalid elements in this table
        # - if multiple symbols bound in the same table
        # - if any bindings conflict with template params

        # TODO: replace with real error handling

        ok = True

        # ensuring each element type is accepted:
        for element in self.elements:
            if isinstance(element, BaseBindElement):
                if not self.accepts_binding_elems:
                    print(f"ERROR: Binding element not permitted in table: {element.loc}")
                    return False
            elif isinstance(element, BaseTypingElement):
                if not self.accepts_typing_elems:
                    print(f"ERROR: Typing element not permitted in table: {element.loc}")
                    return False
            elif isinstance(element, BaseImperativeElement):
                if not self.accepts_imperative_elems:
                    print(f"ERROR: Imperative element not permitted in table: {element.loc}")
                    return False

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


class BaseElement(BaseNode):
    element_kind: ElementKind


# Typing elements:
# used to specify the types of any bound element in this table.

class BaseTypingElement(BaseElement):
    id_name: str

    def __init__(self, loc, id_name: str):
        super().__init__(loc)
        self.id_name = id_name


class TypingValueIDElement(BaseTypingElement):
    type_spec: "BaseTypeSpec"

    def __init__(self, loc, id_name, type_spec: "BaseTypeSpec"):
        super().__init__(loc, id_name)
        self.type_spec = type_spec


# Binding elements:
# used to bind a new variable while providing minimal type information.

class BaseBindElement(BaseElement):
    def __init__(self, loc, id_name):
        super().__init__(loc)
        self.id_name = id_name


class BindOneValueIDElement(BaseBindElement):
    bind_exp: "BaseExp"

    def __init__(self, loc, id_name: str, exp: "BaseExp"):
        super().__init__(loc, id_name)
        self.bind_exp = exp


class BindOneTypeIDElement(BaseBindElement):
    id_name: str
    bind_type_spec: "BaseTypeSpec"

    def __init__(self, loc, id_name: str, type_spec: "BaseTypeSpec"):
        super().__init__(loc, id_name)
        self.bind_type_spec = type_spec


class BaseImperativeElement(BaseElement, metaclass=abc.ABCMeta):
    pass


class ForceEvalElement(BaseImperativeElement):
    discarded_exp: BaseExp

    def __init__(self, loc, discarded_exp):
        super().__init__(loc)
        self.discarded_exp = discarded_exp


#
# GetElementBy / Dot Expressions:
#

class GetElementByNameExp(BaseExp):
    container: BaseExp
    key_name: str

    def __init__(self, loc, container, key_name):
        super().__init__(loc)
        self.container = container
        self.key_name = key_name


class GetElementByIndexExp(BaseExp):
    container: BaseExp
    index: BaseExp
    index_wrapped_by_parens: bool

    def __init__(self, loc, container, index, index_wrapped_by_parens):
        super().__init__(loc)
        self.container = container
        self.index = index
        self.index_wrapped_by_parens = index_wrapped_by_parens


#
# TODO: add/amend AST nodes for pointers, arrays, and slices.
#   - this could include literal expressions
#

#
# TODO: add/amend AST nodes for 'new' expressions using keywords `make` and `push`.
#

#
#
#
