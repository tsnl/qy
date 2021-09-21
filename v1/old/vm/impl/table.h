#pragma once

#include <stddef.h>

// `Table` offers a way to store data that can then be accessed in constant-time.
// Data is stored in contiguous, chained 'blocks' that reside in a fixed-size table.
typedef struct Table Table;
// Although the data-structure is un-typed, this can be useful to manually check declarations:
#define TABLE(T) Table

// create and destroy a list:
Table* tab_new(size_t elem_size, size_t block_elem_count, size_t max_block_count);
void tab_del(Table* tab);

// allocates space for a new element and returns its index:
size_t tab_append(Table* tab);

// gets the pointer to the element in the list at the specified index:
void* tab_gp(Table* tab, size_t id);
