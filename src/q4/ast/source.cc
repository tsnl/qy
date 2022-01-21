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
    Source* newSource = new Source(optParent, std::move(path));
    return s_regMap[path] = newSource;
}
Source* Source::get(Source* optParent, std::filesystem::path path) {
    Source* oldSource = tryLookupSrc(path);
    return (oldSource) ? oldSource : registerSrc(optParent, path);
}

Source::Source(Source* optParent, std::filesystem::path path)
:   m_optParent(optParent), 
    m_path(std::move(path))
{};

Source::~Source() { }

}   // namespace q4