#include "table.h"

#include <assert.h>
#include <stdlib.h>

typedef char* Block;

struct Table {
    Block* blocks;
    size_t block_elem_count;
    size_t elem_size;
    size_t max_block_count;

    size_t count;
    size_t capacity;
};

Table* tab_new(size_t elem_size, size_t block_elem_count, size_t max_block_count) {
    Table* table = malloc(sizeof(Table));

    size_t block_size = elem_size * block_elem_count;
    table->blocks = calloc(block_size, max_block_count);

    table->elem_size = elem_size;
    table->block_elem_count = block_elem_count;
    table->max_block_count = max_block_count;
    table->count = 0;
    table->capacity = block_elem_count * max_block_count;

    return table;
}

void tab_del(Table* table) {
    free(table->blocks);
    free(table);
}

size_t tab_append(Table* table) {
    size_t new_index = table->count++;
    assert(table->count < table->capacity && "table overflow");
    size_t new_block_index = (new_index / table->block_elem_count);
    if (!table->blocks[new_block_index]) {
        // block un-allocated:
        size_t block_size = table->elem_size * table->block_elem_count;
        table->blocks[new_block_index] = malloc(block_size);
    }
    return new_index;
}

void* tab_gp(Table* table, size_t index) {
    assert(index < table->count && "table index out of bounds");

    size_t block_index = (index / table->block_elem_count);
    size_t block_offset = (index % table->block_elem_count) * table->elem_size;

    return table->blocks[block_index] + (block_offset * table->elem_size);
}
