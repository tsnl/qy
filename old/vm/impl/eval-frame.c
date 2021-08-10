#include "eval-frame.h"

#include <stddef.h>
#include <stdlib.h>
#include <stdbool.h>
#include <assert.h>

#include "table.h"

struct EvalFrame {
    EvalFrame* opt_parent_ef;
    int sym_count;
    DefID* sym_names;
    Const* sym_vals;
    uint8_t* sym_init_bitset;
};

int sym_index(EvalFrame* ef, DefID def_id) {
    // todo: try storing definitions in a binary tree to make these lookups
    //       faster.
    for (int i = 0; i < ef->sym_count; i++) {
        if (ef->sym_names[i] == def_id) {
            return i;
        }
    }
    return -1;
}

bool get_sym_is_init(EvalFrame* ef, int sym_index) {
    int word_index = sym_index / 8;
    int word_offset = sym_index % 8;
    return !!(ef->sym_init_bitset[word_index] & (1u << word_offset));
}

void set_sym_is_init(EvalFrame* ef, int sym_index) {
    int word_index = sym_index / 8;
    int word_offset = sym_index % 8;
    ef->sym_init_bitset[word_index] |= (1u << word_offset);
}

//
// Interface:
//

EvalFrame* ef_new(EvalFrame* opt_parent_ef, int sym_count, DefID* mv_sym_names) {
    EvalFrame* efp = malloc(sizeof(EvalFrame));
    
    efp->sym_count = sym_count;
    efp->sym_names = mv_sym_names;
    efp->sym_vals = calloc(sym_count, sizeof(Const));
    
    size_t bits_per_word = 8;   // 8 * sizeof(uint8_t)
    size_t num_words_in_bitset = (
        (sym_count / bits_per_word) +
        ((sym_count % bits_per_word == 0) ? 0 : 1)
    );
    efp->sym_init_bitset = calloc(num_words_in_bitset, bits_per_word);
    
    return efp;
}
void ef_del(EvalFrame* efp) {
    free(efp->sym_names);
    free(efp->sym_vals);
    free(efp->sym_init_bitset);
    free(efp);
}

void ef_init_symbol(EvalFrame* ef, DefID sym_name, Const constant) {
    int si = sym_index(ef, sym_name);
    assert(si >= 0 && "symbol not found");
    set_sym_is_init(ef, si);
    ef->sym_vals[si] = constant;
}
Const const* ef_try_lookup_symbol(EvalFrame* ef, DefID sym_name) {
    int si = sym_index(ef, sym_name);
    if (si >= 0) {
        return ef->sym_vals + si;        
    } else {
        if (ef->opt_parent_ef) {
            return ef_try_lookup_symbol(ef, sym_name);
        } else {
            return NULL;
        }
    }
}
