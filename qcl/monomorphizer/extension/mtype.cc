#include "mtype.hh"

#include <deque>
#include <map>
#include <tuple>

#include "arg-list.hh"
#include "shared-enums.hh"

// TODO: implement this

namespace monomorphizer::mtype {

    using MemWindowKey = std::pair<mtype::TID, bool>;
    using ArrayKey = std::tuple<mtype::TID, mval::ValueID, bool>;
    using FuncKey = std::tuple<mtype::TID, mtype::TID, SES>;

    static bool s_is_init = false;
    static std::deque<TypeKind> s_kind_table{};
    static std::map<arg_list::ArgListID, mtype::TID> s_tuple_tid_cache;
    static std::map<MemWindowKey, mtype::TID> s_ptr_tid_cache;
    static std::map<ArrayKey, mtype::TID> s_array_tid_cache;
    static std::map<MemWindowKey, mtype::TID> s_slice_tid_cache;
    static std::map<FuncKey, mtype::TID> s_func_tid_cache;

    TID mint_tid(TypeKind tk) {
        TID tid = s_kind_table.size();
        s_kind_table.push_back(tk);
        return tid;
    }

    static TID s_unit_tid = 0;
    static TID s_u1_tid = 0;
    static TID s_u8_tid = 0;
    static TID s_u16_tid = 0;
    static TID s_u32_tid = 0;
    static TID s_u64_tid = 0;
    static TID s_s8_tid = 0;
    static TID s_s16_tid = 0;
    static TID s_s32_tid = 0;
    static TID s_s64_tid = 0;
    static TID s_f32_tid = 0;
    static TID s_f64_tid = 0;
    static TID s_str_tid = 0;

    void ensure_init() {
        if (!s_is_init) {
            s_unit_tid = mint_tid(TypeKind::Unit);
            s_u1_tid = mint_tid(TypeKind::U1);
            s_u8_tid = mint_tid(TypeKind::U8);
            s_u16_tid = mint_tid(TypeKind::U16);
            s_u32_tid = mint_tid(TypeKind::U32);
            s_u64_tid = mint_tid(TypeKind::U64);
            s_s8_tid = mint_tid(TypeKind::S8);
            s_s16_tid = mint_tid(TypeKind::S16);
            s_s32_tid = mint_tid(TypeKind::S32);
            s_s64_tid = mint_tid(TypeKind::S64);
            s_f32_tid = mint_tid(TypeKind::F32);
            s_f64_tid = mint_tid(TypeKind::F64);
            s_str_tid = mint_tid(TypeKind::String);
            s_is_init = true;
        }
    }

    TID get_unit_tid() {
        return s_unit_tid;
    }
    TID get_u1_tid() {
        return s_u1_tid;
    }
    TID get_u8_tid() {
        return s_u8_tid;
    }
    TID get_u16_tid() {
        return s_u16_tid;
    }
    TID get_u32_tid() {
        return s_u32_tid;
    }
    TID get_u64_tid() {
        return s_u64_tid;
    }
    TID get_s8_tid() {
        return s_s8_tid;
    }
    TID get_s16_tid() {
        return s_s16_tid;
    }
    TID get_s32_tid() {
        return s_s32_tid;
    }
    TID get_s64_tid() {
        return s_s64_tid;
    }
    TID get_f32_tid() {
        return s_f32_tid;
    }
    TID get_f64_tid() {
        return s_f64_tid;
    }
    TID get_string_tid() {
        return s_str_tid;
    }

    // todo: implement these functions
    TID get_tuple_tid(arg_list::ArgListID arg_list_id) {
        auto it = s_tuple_tid_cache.find(arg_list_id);
        if (it != s_tuple_tid_cache.end()) {
            return it->second;
        } else {
            auto id = mint_tid(TypeKind::Tuple);
            s_tuple_tid_cache.insert({arg_list_id, id});
            return id;
        }
    }

    TID get_ptr_tid(TID ptd_tid, bool contents_is_mut) {
        MemWindowKey const key = {ptd_tid, contents_is_mut};
        auto it = s_ptr_tid_cache.find(key);
        if (it != s_ptr_tid_cache.end()) {
            return it->second;
        } else {
            auto id = mint_tid(TypeKind::Pointer);
            s_ptr_tid_cache.insert({key, id});
            return id;
        }
    }

    TID get_array_tid(
        TID ptd_tid, 
        mval::ValueID count_val_id, 
        bool contents_is_mut
    ) {
        ArrayKey const key = {ptd_tid, count_val_id, contents_is_mut};
        auto it = s_array_tid_cache.find(key);
        if (it != s_array_tid_cache.end()) {
            return it->second;
        } else {
            auto id = mint_tid(TypeKind::Array);
            s_array_tid_cache.insert({key, id});
            return id;
        }
    }

    TID get_slice_tid(TID ptd_tid, bool contents_is_mut) {
        MemWindowKey const key = {ptd_tid, contents_is_mut};
        auto it = s_slice_tid_cache.find(key);
        if (it != s_slice_tid_cache.end()) {
            return it->second;
        } else {
            auto id = mint_tid(TypeKind::Slice);
            s_slice_tid_cache.insert({key, id});
            return id;
        }
    }

    TID get_function_tid(TID arg_tid, TID ret_tid, SES ses) {
        FuncKey const key = {arg_tid, ret_tid, ses};
        auto it = s_func_tid_cache.find(key);
        if (it != s_func_tid_cache.end()) {
            return it->second;
        } else {
            auto id = mint_tid(TypeKind::Function);
            s_func_tid_cache.insert({key, id});
            return id;
        }
    }

}