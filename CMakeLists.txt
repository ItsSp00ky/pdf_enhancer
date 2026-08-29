cmake_minimum_required(VERSION 3.21)
project(pdf_enhancer_cpp LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_AUTOMOC ON)
set(CMAKE_AUTOUIC ON)
set(CMAKE_AUTORCC ON)

if(MSVC AND MSVC_VERSION GREATER_EQUAL 1940 AND NOT DEFINED OpenCV_RUNTIME)
    # OpenCV 4.12 prebuilt package ships vc16 binaries; newer MSVC is ABI-compatible.
    set(OpenCV_RUNTIME vc16 CACHE STRING "Force OpenCV runtime for prebuilt package" FORCE)
endif()

find_package(Qt6 REQUIRED COMPONENTS Core Gui Widgets PrintSupport Pdf Concurrent)
find_package(OpenCV REQUIRED)

# WIN32 hides the console/terminal window on Windows
add_executable(pdf_enhancer_cpp WIN32
    src/main.cpp
    src/MainWindow.h
    src/MainWindow.cpp
    src/DocumentProcessor.h
    src/DocumentProcessor.cpp
)

# Embed Windows app icon into the .exe
if(WIN32)
    set(APP_ICON_RESOURCE "${CMAKE_CURRENT_BINARY_DIR}/app_icon.rc")
    file(WRITE "${APP_ICON_RESOURCE}" "IDI_ICON1 ICON DISCARDABLE \"${CMAKE_CURRENT_SOURCE_DIR}/scanner.ico\"\n")
    target_sources(pdf_enhancer_cpp PRIVATE "${APP_ICON_RESOURCE}")
endif()

target_include_directories(pdf_enhancer_cpp PRIVATE ${OpenCV_INCLUDE_DIRS})

target_link_libraries(pdf_enhancer_cpp PRIVATE
    Qt6::Core
    Qt6::Gui
    Qt6::Widgets
    Qt6::PrintSupport
    Qt6::Pdf
    Qt6::Concurrent
    ${OpenCV_LIBS}
)
