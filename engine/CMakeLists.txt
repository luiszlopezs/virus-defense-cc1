cmake_minimum_required(VERSION 3.16)
project(virus_engine LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

add_executable(virus_engine
    src/main.cpp
    src/LinkedList.cpp
    src/BST.cpp
    src/GameEngine.cpp
)

target_include_directories(virus_engine PRIVATE src)
