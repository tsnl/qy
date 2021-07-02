#pragma once

#include <stddef.h>

typedef size_t TypeID;

// rtti: run-time type info: mapped into existence by the 'inference' system.
// - IDEA: make all this 'automatic', i.e. computed from expressions with error upon failure.
// - if, during template expansion, we generate a type un-mapped by the old system, we have a problem.
// - instead, why not use an independent type solver that we map back to typer IDs after running?

// void vm_map_unit_tid(VM* vm, TypeID unit_tid);
// void vm_map_int_tid(VM* vm, TypeID sint_tid, uint8_t width_in_bits, bool is_signed);
// void vm_map_float_tid(VM* vm, TypeID float_tid, uint8_t width_in_bits);
// void vm_map_string_tid(VM* vm, TypeID string_tid);
// void vm_map_tuple_tid(VM* vm, TypeID tuple_tid, uint64_t tuple_count, TypeID* elem_tids);
// void vm_map_ptr_tid(VM* vm, TypeID pointee_tid, bool is_mut);
// void vm_map_array_tid(VM* vm, TypeID array_tid, TypeID elem_tid, bool is_mut);
// void vm_map_slice_tid(VM* vm, TypeID slice_tid, TypeID elem_tid, bool is_mut);
// void vm_map_adt_tid(VM* vm, TypeID struct_tid, AdtKind adt_kind, uint64_t elem_count, TypeID* elem_tid_list);
// void vm_map_fn_tid(VM* vm, TypeID arg_tid, TypeID ret_tid);
