#include <bit>
#include <climits>
#include <cstdio>
#include <limits>
static_assert(CHAR_BIT == 8 && sizeof(float) == 4);
static_assert(std::numeric_limits<float>::is_iec559);
static_assert(std::numeric_limits<float>::radix == 2 && std::numeric_limits<float>::digits == 24);
static_assert(std::numeric_limits<float>::min_exponent == -125 && std::numeric_limits<float>::max_exponent == 128);
static_assert(std::endian::native == std::endian::little);
static_assert(std::bit_cast<unsigned int>(1.0F) == 0x3f800000U);
int main() { const float value = 1.0F; return std::fwrite(&value, sizeof(value), 1, stdout) == 1 ? 0 : 1; }
