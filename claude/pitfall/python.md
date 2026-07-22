# Python 踩坑记录

## 2026-06-05 - Python ctypes 读 64 位进程内存：必须显式设 restype/argtypes，否则地址被截断

**现象**: 用 ctypes 调 ReadProcessMemory/VirtualQueryEx 读 64 位进程内存，读取全失败或读到错误地址，地址大于 32 位时尤甚。
**根因**: ctypes 默认把函数返回值和未声明的指针/地址参数当 c_int(32位)，64 位地址被截断成低 32 位，传给 Win32 API 即指向错误内存。MEMORY_BASIC_INFORMATION 等结构体在 64 位下还有对齐填充字段(__alignment)，缺了会错位。
**解决**: 显式声明每个 Win32 函数的 restype/argtypes：句柄/地址用 c_void_p、大小用 c_size_t、返回的地址/大小用 c_void_p/c_size_t；结构体按 64 位布局补 __alignment 填充。并检测 sys.maxsize 确保用 64 位 Python（32 位 Python 无法完整读 64 位进程）。
**标签**: python, ctypes, windows-api, readprocessmemory, virtualqueryex, 64位, 地址截断, restype, argtypes
