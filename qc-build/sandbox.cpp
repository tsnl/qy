#include "sandbox.hpp"

#include <cstdint>
#include <string>

// bind x = IntExpression
int32_t x
{
	2
}

// bind y = IntExpression
static int32_t y
{
	4
}

// bind w = ProcCallExpression
static int32_t w
{
	<NotImplemented:ProcCallExpression>
}

// bind j = ProcCallExpression
static int32_t j
{
	<NotImplemented:ProcCallExpression>
}

// bind b1 = IntExpression
static bool b1
{
	true
}

// bind b2 = IntExpression
static bool b2
{
	false
}

// bind m = BinaryOpExpression
static bool m
{
	<NotImplemented:BinaryOpExpression>
}

// bind x = IntExpression
static int32_t x
{
	42
}

// bind y = FloatExpression
static double y
{
	<NotImplemented:FloatExpression>
}

// bind z = FloatExpression
static float z
{
	<NotImplemented:FloatExpression>
}

// bind w = IntExpression
static uint64_t w
{
	0x256uLL
}

// bind s1 = StringExpression
static std::string s1
{
	<NotImplemented:StringExpression>
}

// bind s2 = StringExpression
std::string s2
{
	<NotImplemented:StringExpression>
}

