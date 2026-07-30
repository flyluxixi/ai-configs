# Python 踩坑记录

## 2026-06-05 - Python ctypes 读 64 位进程内存：必须显式设 restype/argtypes，否则地址被截断

**现象**: 用 ctypes 调 ReadProcessMemory/VirtualQueryEx 读 64 位进程内存，读取全失败或读到错误地址，地址大于 32 位时尤甚。
**根因**: ctypes 默认把函数返回值和未声明的指针/地址参数当 c_int(32位)，64 位地址被截断成低 32 位，传给 Win32 API 即指向错误内存。MEMORY_BASIC_INFORMATION 等结构体在 64 位下还有对齐填充字段(__alignment)，缺了会错位。
**解决**: 显式声明每个 Win32 函数的 restype/argtypes：句柄/地址用 c_void_p、大小用 c_size_t、返回的地址/大小用 c_void_p/c_size_t；结构体按 64 位布局补 __alignment 填充。并检测 sys.maxsize 确保用 64 位 Python（32 位 Python 无法完整读 64 位进程）。
**标签**: python, ctypes, windows-api, readprocessmemory, virtualqueryex, 64位, 地址截断, restype, argtypes

## 2026-07-30 - Debian apt 装的 pycryptodome 在 Cryptodome 命名空间，import Crypto 报 ModuleNotFoundError

**现象**: 容器(Debian 12)里 `apt install python3-pycryptodome` 明明成功，`from Crypto.Cipher import AES` 却报 `ModuleNotFoundError: No module named 'Crypto'`；一度误判成"包没装上"。
**根因**: Debian 打包的 python3-pycryptodome 装进 `Cryptodome` 命名空间（为与历史 pycrypto 的 `Crypto` 命名空间共存避冲突），而 `pip install pycryptodome` 装的是 `Crypto` 命名空间。同一个库、两套顶层包名，取决于用 apt 还是 pip 装。
**解决**: 双导入兜底兼容两种来源：`try: from Crypto.Cipher import AES` / `except ImportError: from Cryptodome.Cipher import AES`。或统一用 pip 装（得 `Crypto`）。排查时先 `python3 -c "import Cryptodome; print(Cryptodome.__version__)"` 确认装没装、装哪个命名空间，别被 `import Crypto` 失败误导成"没装"。
**标签**: python, pycryptodome, Cryptodome, Crypto, debian, apt, pip, 命名空间, ModuleNotFoundError, 依赖安装
