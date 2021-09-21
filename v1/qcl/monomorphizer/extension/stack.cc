#include "stack.hh"

#include <map>
#include <vector>

#include "intern.hh"
#include "panic.hh"

namespace monomorphizer::stack {

    struct Frame {
        std::map<intern::IntStr, size_t> id_map;

        Frame() = default;
    };

    struct Stack {
        std::vector<Frame> frames;

        Stack() = default;
    };

    size_t lookup(Stack* stack, intern::IntStr int_str_id) {
        for (size_t i = 0; i <= stack->frames.size(); i++) {
            size_t frame_index = stack->frames.size() - (1+i);
            Frame const* frame_ref = &stack->frames[frame_index];
            auto it = frame_ref->id_map.find(int_str_id);
            if (it != frame_ref->id_map.end()) {
                return it->second;
            }
        }
        throw new Panic("Undefined ID in `lookup_v_in_stack`");
    }

}

namespace monomorphizer::stack {

    Stack* create_stack() {
        return new Stack();
    }
    void destroy_stack(Stack* st) {
        delete st;
    }

    void push_stack_frame(Stack* stack) {
        stack->frames.emplace_back();
    }
    void pop_stack_frame(Stack* stack) {
        stack->frames.pop_back();
    }

    void def_t_in_stack(Stack* stack, intern::IntStr int_str_id, mtype::TID tid) {
        stack->frames.back().id_map[int_str_id] = tid;
    }
    void def_v_in_stack(Stack* stack, intern::IntStr int_str_id, mval::VID vid) {
        stack->frames.back().id_map[int_str_id] = vid;
    }
    mval::VID lookup_v_in_stack(Stack* stack, intern::IntStr int_str_id) { return lookup(stack, int_str_id); }
    mtype::TID     lookup_t_in_stack(Stack* stack, intern::IntStr int_str_id) { return lookup(stack, int_str_id); }

}