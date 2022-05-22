#pragma once

typedef float  f32;
typedef double f64;

static_assert(sizeof(f32) == 4, "Expected sizeof(f32) == 4");
static_assert(sizeof(f64) == 8, "Expected sizeof(f64) == 8");

