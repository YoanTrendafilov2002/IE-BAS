#pragma once

#include <cstdint>

namespace irrigation::front { class TimeSyncManager { public: bool sync(); std::uint32_t now() const; }; }
