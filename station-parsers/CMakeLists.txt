cmake_minimum_required(VERSION 3.16)
project(station_parsers LANGUAGES C CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

add_executable(lufft_data Data.c)
add_executable(lufft_parser LuftParser.cpp)

if(WIN32)
  add_executable(vaisala_parser WIN32 VaisalaParser.cpp)
endif()
