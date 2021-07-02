#pragma once

#include <cstdint>

#include <deque>
#include <string>
#include <map>

#include "int-str.hh"
#include "value.hh"
#include "frame.hh"
#include "func.hh"
#include "rtti.hh"

namespace qcl {

    class VM_Impl {
      public:
        using FuncID = uint64_t;
      private:
        struct FuncInfo {
            FuncDecl decl;
            FuncDefn defn;
        };

      private:
        std::deque<Frame> m_frame_stack;
        std::map<std::string const, IntStr> m_interned_str_map;
        std::deque<FuncInfo> m_func_info_list;

      //
      // core properties:
      //

      public:
        Frame& global_frame() { return m_frame_stack[0]; }
        FuncDecl& func_decl(FuncID func_id) { return m_func_info_list[func_id].decl; }
        FuncDefn& func_defn(FuncID func_id) { return m_func_info_list[func_id].defn; }

      //
      // interface methods:
      //

      // string interning: str -> unique int ID conversion
      public:
        IntStr intern(char const* null_terminated_bytes);

      // function building: define the contents of functions
      public:
        FuncID declare_func(TID fn_type_tid);
        // todo: define stuff using FuncID fn_id: each element gets a different 'build' fn

      // global frame manipulation: define symbols in the global scope.
      public:


      public:
        // todo: first generate synthetic function definitions for all functions
        //      - turn implicit arguments into an explicit 'closure' object
        //      - in LLVM, we can use trampolines to eliminate the closed argument
        // todo: next, generate initializers for every global sub-module field
        //      - involves 'flattening' modules into the top frame.
        //      - involves renaming module-level IDs before accessing.
        // todo: allow user code to initialize code-func and initializer defs.
    };

}   // namespace qcl
