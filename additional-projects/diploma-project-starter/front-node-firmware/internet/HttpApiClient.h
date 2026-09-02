#pragma once

#include <cstddef>
#include <cstdint>

namespace irrigation::front { class HttpApiClient { public: bool post(const char* path, const std::uint8_t* body, std::size_t size); }; }
