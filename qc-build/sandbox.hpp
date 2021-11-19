#pragma once

#include <cstdint>
#include <string>

// extern x
extern int32_t x;

// extern x
extern int32_t x;

// extern hello
extern <NotImplemented:(i32)=>i32> hello;

// extern wrongPhi
extern <NotImplemented:(bool,i32,i32)=>i32> wrongPhi;

// extern s2
extern std::string s2;

// extern vec3f
extern <NotImplemented:(f32,f32,f32)=>struct#8410{x:f32,y:f32,z:f32}> vec3f;

// extern v3f_add
extern <NotImplemented:(struct#83d4{x:f32,y:f32,z:f32},struct#843a{x:f32,y:f32,z:f32})=>struct#8416{x:f32,y:f32,z:f32}> v3f_add;

// extern v3f_scale
extern <NotImplemented:(struct#845e{x:f32,y:f32,z:f32},f32)=>struct#85d2{x:f32,y:f32,z:f32}> v3f_scale;

