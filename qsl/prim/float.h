#pragma once

typedef float       f32;
typedef double      f64;
typedef long double f128;

static_assert(sizeof(f32) == 4, "Expected sizeof(f32) == 4");
static_assert(sizeof(f64) == 8, "Expected sizeof(f64) == 8");
static_assert(sizeof(f128) == 16, "Expected sizeof(f128) == 16");
