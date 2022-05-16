#pragma once

#include <stdint.h>
#include <assert.h>

typedef char i8;
typedef short i16;
typedef int i32;
typedef long long i64;

typedef unsigned char u8;
typedef unsigned short u16;
typedef unsigned int u32;
typedef unsigned long long u64;

static_assert(sizeof(i8) == 1,  "Expected sizeof(i8)  == 1");
static_assert(sizeof(i16) == 2, "Expected sizeof(i16) == 2");
static_assert(sizeof(i32) == 4, "Expected sizeof(i32) == 4");
static_assert(sizeof(i64) == 8, "Expected sizeof(i64) == 8");

static_assert(sizeof(u8) == 1,  "Expected sizeof(u8)  == 1");
static_assert(sizeof(u16) == 2, "Expected sizeof(u16) == 2");
static_assert(sizeof(u32) == 4, "Expected sizeof(u32) == 4");
static_assert(sizeof(u64) == 8, "Expected sizeof(u64) == 8");
