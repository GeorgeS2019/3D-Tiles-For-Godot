#ifndef ERROR_NAMES_H
#define ERROR_NAMES_H

#if defined (CESIUM_GD_EXT)
#include "magic_enum.hpp"

#define REFLECT_ERR_NAME(x) magic_enum::enum_name(x).data()

#elif defined(CESIUM_GD_MODULE)

#define REFLECT_ERR_NAME(x) error_names[x]

#endif
#endif