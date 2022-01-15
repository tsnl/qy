#pragma once

#include <map>
#include <filesystem>
#include <cstdint>

namespace q4 {

class Source {
  private:
    inline static int const DEFAULT_PER_SOURCE_HEAP_SIZE_IN_BYTES = 4LLU*1024*1024;
    static std::map<std::filesystem::path, Source*> s_regMap;
  private:
    Source* m_optParent;
    std::filesystem::path m_path;
    uint8_t* const m_heap;
    int m_heapUseInBytes;
    int const m_heapSizeInBytes;
  private:
    static Source* tryLookupSrc(std::filesystem::path path);
    static Source* registerSrc(Source* optParent, std::filesystem::path path);
  private:
    Source(Source* optParent, std::filesystem::path path, uint8_t* heap, int heapUseInBytes, int heapSizeInBytes);
    ~Source();
  public:
    static Source* get(Source* optParent, std::filesystem::path path);
  public:
    inline std::filesystem::path const& path() const { return m_path; }
  public:
    void* rawAlloc(int sizeInBytes);
    
    template <typename T, typename... TArgs>
    T* alloc(TArgs... args) { 
        T* mem = static_cast<T*>(rawAlloc(sizeof(T))); 
        return new(mem) T(args...); 
    }
};

}   // namespace q4
