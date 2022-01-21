#pragma once

#include <map>
#include <filesystem>
#include <cstdint>

namespace q4 {

class Source {
  private:
    static std::map<std::filesystem::path, Source*> s_regMap;
  private:
    Source* m_optParent;
    std::filesystem::path m_path;
  private:
    static Source* tryLookupSrc(std::filesystem::path path);
    static Source* registerSrc(Source* optParent, std::filesystem::path path);
  private:
    Source(Source* optParent, std::filesystem::path path);
    ~Source();
  public:
    static Source* get(Source* optParent, std::filesystem::path path);
  public:
    inline std::filesystem::path const& path() const { return m_path; }
};

}   // namespace q4
