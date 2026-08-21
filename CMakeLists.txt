cmake_minimum_required(VERSION 3.20)
project(pitpy
    VERSION 0.1.0
    DESCRIPTION "Motor de diseno geometrico de pit: bancos, bermas y rampa"
    LANGUAGES CXX
)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

# ============================================================================
# Nucleo header-only
# ============================================================================
add_library(pitpy_core INTERFACE)
target_include_directories(pitpy_core INTERFACE
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
    $<INSTALL_INTERFACE:include>
)
target_compile_features(pitpy_core INTERFACE cxx_std_20)

# ============================================================================
# Bindings de Python (nanobind via scikit-build-core)
# ============================================================================
option(PITPY_BUILD_PYTHON "Build Python bindings" ON)

if(PITPY_BUILD_PYTHON)
    find_package(Python 3.10
        REQUIRED COMPONENTS Interpreter Development.Module
        OPTIONAL_COMPONENTS Development.SABIModule
    )

    execute_process(
        COMMAND "${Python_EXECUTABLE}" -m nanobind --cmake_dir
        OUTPUT_STRIP_TRAILING_WHITESPACE
        OUTPUT_VARIABLE NB_DIR
        RESULT_VARIABLE NB_RESULT
    )

    if(NB_RESULT EQUAL 0 AND EXISTS "${NB_DIR}")
        list(APPEND CMAKE_PREFIX_PATH "${NB_DIR}")
        find_package(nanobind CONFIG REQUIRED)

        # STABLE_ABI: una rueda por plataforma sirve para 3.12+ en vez de una por
        # version de Python. NB_STATIC: no arrastra un .so extra de nanobind.
        nanobind_add_module(_nucleo
            STABLE_ABI
            NB_STATIC
            bindings/bindings.cpp
        )
        target_link_libraries(_nucleo PRIVATE pitpy_core)

        install(TARGETS _nucleo
            LIBRARY DESTINATION pitpy
            RUNTIME DESTINATION pitpy
            ARCHIVE DESTINATION pitpy
        )
    else()
        message(FATAL_ERROR
            "No se encontro nanobind, asi que el paquete saldria sin nucleo.\n"
            "Instalar con: pip install nanobind"
        )
    endif()
endif()
