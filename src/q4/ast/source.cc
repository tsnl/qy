#include "q4/ast/source.hh"

#include <cassert>
#include <filesystem>

namespace q4 {

std::map<std::filesystem::path, Source*> Source::s_regMap;

Source* Source::tryLookupSrc(std::filesystem::path path) {
    auto it = s_regMap.find(path);
    return (it == s_regMap.end()) ? nullptr : it->second;
}
Source* Source::registerSrc(Source* optParent, std::filesystem::path path) {
    size_t const slabSizeInBytes = DEFAULT_PER_SOURCE_HEAP_SIZE_IN_BYTES;
    uint8_t* const slab = new uint8_t[slabSizeInBytes];
    Source* newSource = new(slab) Source(optParent, std::move(path), slab, sizeof(Source), DEFAULT_PER_SOURCE_HEAP_SIZE_IN_BYTES);
    return s_regMap[path] = newSource;
}
Source* Source::get(Source* optParent, std::filesystem::path path) {
    Source* oldSource = tryLookupSrc(path);
    return (oldSource) ? oldSource : registerSrc(optParent, path);
}

Source::Source(Source* optParent, std::filesystem::path path, uint8_t* heap, int heapUseInBytes, int heapSizeInBytes)
:   m_optParent(optParent), 
    m_path(std::move(path)), 
    m_heap(heap),
    m_heapUseInBytes(heapUseInBytes),
    m_heapSizeInBytes(heapSizeInBytes)
{
    assert(m_heapSizeInBytes > 0 && "Initial heap size in bytes overflow");
    assert(m_heapUseInBytes >= 0 && "Initial heap usage in bytes overflow"); 
};

Source::~Source() { 
    delete[] m_heap; 
}

void* Source::rawAlloc(int allocSizeInBytes) {
    assert(m_heapSizeInBytes > 0 && "Heap size in bytes overflow detected before 'alloc'");
    assert(m_heapUseInBytes >= 0 && "Heap usage in bytes overflow detected before 'alloc'");
    
    int newHeapUseInBytes = m_heapUseInBytes + allocSizeInBytes;
    assert(newHeapUseInBytes >= 0 && "Heap usage in bytes overflow detected after 'alloc'");
    assert(newHeapUseInBytes <= m_heapSizeInBytes && "Heap overflow: required usage exceeds available capacity");
    
    uint8_t* mem = m_heap + m_heapUseInBytes;
    m_heapUseInBytes = newHeapUseInBytes;
    return static_cast<void*>(mem);
}

}   // namespace q4