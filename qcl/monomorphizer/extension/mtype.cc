#include "mtype.hh"

#include <deque>
#include <map>
#include <tuple>

#include "arg-list.hh"
#include "shared-enums.hh"

// TODO: implement this

namespace monomorphizer::mtype {

    using MemWindowKey = std::pair<mtype::MTypeID, bool>;
    using FuncKey = std::tuple<mtype::MTypeID, mtype::MTypeID, SES>;

    static bool s_is_init = false;
    static std::deque<TypeKind> s_kind_table{};
    static std::map<arg_list::ArgListID, mtype::MTypeID> s_tuple_tid_cache;
    static std::map<MemWindowKey, mtype::MTypeID> s_ptr_tid_cache;
    static std::map<MemWindowKey, mtype::MTypeID> s_array_tid_cache;
    static std::map<MemWindowKey, mtype::MTypeID> s_slice_tid_cache;
    static std::map<FuncKey, mtype::MTypeID> s_func_tid_cache;

    MTypeID mint_tid(TypeKind tk) {
        MTypeID tid = s_kind_table.size();
        s_kind_table.push_back(tk);
        return tid;
    }

    static MTypeID s_unit_tid = 0;
    static MTypeID s_u1_tid = 0;
    static MTypeID s_u8_tid = 0;
    static MTypeID s_u16_tid = 0;
    static MTypeID s_u32_tid = 0;
    static MTypeID s_u64_tid = 0;
    static MTypeID s_s8_tid = 0;
    static MTypeID s_s16_tid = 0;
    static MTypeID s_s32_tid = 0;
    static MTypeID s_s64_tid = 0;
    static MTypeID s_f32_tid = 0;
    static MTypeID s_f64_tid = 0;
    static MTypeID s_str_tid = 0;

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

    MTypeID get_unit_tid() {
        return s_unit_tid;
    }
    MTypeID get_u1_tid() {
        return s_u1_tid;
    }
    MTypeID get_u8_tid() {
        return s_u8_tid;
    }
    MTypeID get_u16_tid() {
        return s_u16_tid;
    }
    MTypeID get_u32_tid() {
        return s_u32_tid;
    }
    MTypeID get_u64_tid() {
        return s_u64_tid;
    }
    MTypeID get_s8_tid() {
        return s_s8_tid;
    }
    MTypeID get_s16_tid() {
        return s_s16_tid;
    }
    MTypeID get_s32_tid() {
        return s_s32_tid;
    }
    MTypeID get_s64_tid() {
        return s_s64_tid;
    }
    MTypeID get_f32_tid() {
        return s_f32_tid;
    }
    MTypeID get_f64_tid() {
        return s_f64_tid;
    }
    MTypeID get_str_tid() {
        return s_str_tid;
    }

    // todo: implement these functions
    MTypeID get_tuple_tid(arg_list::ArgListID arg_list_id) {
        auto it = s_tuple_tid_cache.find(arg_list_id);
        if (it != s_tuple_tid_cache.end()) {
            return it->second;
        } else {
            auto id = mint_tid(TypeKind::Tuple);
            s_tuple_tid_cache.insert({arg_list_id, id});
            return id;
        }
    }

    MTypeID get_ptr_tid(MTypeID ptd_tid, bool contents_is_mut) {
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

    MTypeID get_array_tid(MTypeID ptd_tid, bool contents_is_mut) {
        MemWindowKey const key = {ptd_tid, contents_is_mut};
        auto it = s_array_tid_cache.find(key);
        if (it != s_array_tid_cache.end()) {
            return it->second;
        } else {
            auto id = mint_tid(TypeKind::Array);
            s_array_tid_cache.insert({key, id});
            return id;
        }
    }

    MTypeID get_slice_tid(MTypeID ptd_tid, bool contents_is_mut) {
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

    MTypeID get_function_tid(MTypeID arg_tid, MTypeID ret_tid, SES ses) {
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