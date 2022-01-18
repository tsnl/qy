#pragma once

#include <stack>
#include <cstdint>

#include "q4/ast/ast.hh"
#include "q4/util/intern.hh"
#include "scope.hh"
#include "frame.hh"
#include "object.hh"

namespace q4 {

    class Interp {
    private:
        std::stack<Scope*> m_staticStack;
        std::stack<Frame*> m_dynamicStack;
    public:
        Interp(bool print_stmt_output);
    public:
        void loadStmt(BaseStmt* stmt);
    private:
        void pushScope(Scope* scope);
        void popScope();
        Scope* topScope() const;
    private:
        Object* tryLookupValue(IntStr symName);
        bool trySetValue(IntStr symName, Object* v);
    private:
        void evalStmt(PStmt stmt);
        Object* evalExp(PExp exp);
    private:
        Object* getBoolObj(bool v) const;
        Object* newInt8Obj(int8_t v);
        Object* newInt16Obj(int16_t v);
        Object* newInt32Obj(int32_t v);
        Object* newInt64Obj(int64_t v);
        Object* newUInt8Obj(uint8_t v);
        Object* newUInt16Obj(uint16_t v);
        Object* newUInt32Obj(uint32_t v);
        Object* newUInt64Obj(uint64_t v);
        Object* newFloat32Obj(float v);
        Object* newFloat64Obj(double v);
        Object* newRuneObj(int32_t v);
        Object* newStringObj(size_t count, int32_t* runes);
    private:
        Object* newClosureObj(PExp closureExp);
        Object* newAotClosureObj(PExp aotClosureExp);
        Object* castInterfaceInstanceObj(Object* interface, Object* input);
        Object* sendMessageObj(Object* self, IntStr msgName, Object* optExpectedInterface);
    private:
        Object* primitiveType_Bool() const;
        Object* primitiveType_UInt8() const;
        Object* primitiveType_UInt16() const;
        Object* primitiveType_UInt32() const;
        Object* primitiveType_UInt64() const;
        Object* primitiveType_Int8() const;
        Object* primitiveType_Int16() const;
        Object* primitiveType_Int32() const;
        Object* primitiveType_Int64() const;
        Object* primitiveType_Float32() const;
        Object* primitiveType_Float64() const;
        Object* primitiveType_Rune() const;
        Object* primitiveType_String() const;
    private:
        Object* getStructType(PExp structExp);
        Object* getEnumType(PExp enumExp);
        Object* getInterfaceType(PExp interfaceExp);
    };
}