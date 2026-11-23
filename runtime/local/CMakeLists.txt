cmake_minimum_required(VERSION 3.22)
project(refbound_local LANGUAGES C CXX CUDA)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

set(backend "${CMAKE_CURRENT_SOURCE_DIR}/../backend")
add_subdirectory("${backend}" backend)
add_executable(refbound-local src/native.cpp src/work_counts.cpp)
target_include_directories(refbound-local PRIVATE
    "${backend}/include" "${backend}/src" "${backend}/ggml/include"
    "${backend}/ggml/src" "${backend}/common" "${backend}/vendor"
    "${CMAKE_CUDA_TOOLKIT_INCLUDE_DIRECTORIES}")
target_link_libraries(refbound-local PRIVATE llama ggml ggml-cuda ${CMAKE_DL_LIBS})
foreach(symbol IN ITEMS cudaLaunchKernel cudaLaunchKernelExC cudaMemcpyAsync
        cudaMemcpy cudaMemcpy2DAsync cudaMalloc cudaMallocAsync
        cudaStreamSynchronize cudaDeviceSynchronize)
    target_link_options(refbound-local PRIVATE "LINKER:--wrap=${symbol}")
endforeach()
target_link_options(refbound-local PRIVATE "LINKER:-Map=${CMAKE_BINARY_DIR}/local-link.map")
