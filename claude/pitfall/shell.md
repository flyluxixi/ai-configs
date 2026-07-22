# Shell / 运维操作踩坑记录

## 2026-06-10 - 给「下线服务」叠加不必要的备份整理步骤，空变量+sudo+通配符把 / 顶层权限全改坏

**现象**: 任务只是「下线一个服务」，却在自行添加的「备份整理」环节连环出错，最终一条 `sudo chown user:user "$BK"/*` 因 $BK 为空退化成 `sudo chown user:user /*` + `chmod 600 /*`，把 / 下所有顶层目录属主改成普通用户、权限改 600。SSH 认证能过但起不了 shell（`/bin/bash: Permission denied`），整机只能靠带外 root 抢救。
**根因**: 两层叠加。①【流程，主因】给简单任务叠加了它根本不需要的高风险步骤：备份时用 `sudo cp` 复制 root 拥有的系统配置（nginx/systemd），使备份副本变成 root 属主；随后 `chmod -R 700 "$BK"` 想锁定备份目录、对 root 属主文件失败；又专门写第二条命令去「补救」这个自己造出来的属主问题——补救命令即 `sudo chown $(whoami) "$BK"/*`。整条 chown/chmod 与「下线服务」毫无关系，是自造问题再补救。②【机制】第一条命令 `set -e` 在 chmod 失败处提前退出，跳过了写「备份路径标记文件」的最后一句；第二条 `BK=$(cat 标记文件)` 读到空串，`"$BK"/*` 退化为 `/*`（chmod/chown 默认跟随 /bin→/usr/bin 等软链打到本体）；普通用户丢失目录执行位后无法穿过 /usr，SSH 在起登录 shell 阶段失败。
**解决（恢复 runbook）**:
- 关键事实：**只有 root 能修**——root 有 CAP_DAC_OVERRIDE，可无视目录缺失的执行(搜索)位 exec 程序、穿过 /usr；**普通用户即便已是这些目录的属主也不行**（无执行位穿不过去），所以 SSH（普通用户起不了 shell、root 多半无密码登录/StrictModes 拒）和普通用户登控制台都救不了，必须拿到 **root 的非 SSH 入口**。
- 入口（任选其一）：① 厂商 **VM/VNC 控制台**，用 **root** 登录（控制台密码登录走本地 PAM，与 sshd 的 PasswordAuthentication 无关）；② **救援模式**：挂临时系统、mount 故障盘到挂载点（如 /mnt/sysroot）后在挂载点上修；③ 故障前**已开着的 root 终端**（进程在内存，root 可 exec）；④ 已在跑的 **root 运维 agent**（salt-minion/puppet 等）从 LAN 控制端推命令。
- 第 0 步：先 `ls -la /` 找出**所有**属主被改成普通用户、权限变 600 的顶层条目（可能含 /apps、/data 等自定义目录，别只改下面列的）。
- 在「正在运行的系统」上以 root 执行（**绝不加 -R**；/bin /sbin /lib /lib64 是软链，当时被穿透打到 /usr/* 本体，故直接修 /usr/*）：
  ```
  chown root:root /usr /usr/bin /usr/sbin /usr/lib /usr/lib64 /etc /var /opt /srv /boot /home /media /mnt /run /dev /tmp /root /apps 2>/dev/null
  chmod 755 /usr /usr/bin /usr/sbin /usr/lib /usr/lib64 /etc /var /opt /srv /boot /home /media /mnt /run /dev /apps
  chmod 1777 /tmp
  chmod 700  /root
  ```
  救援模式下给每个路径加挂载点前缀（如 `/mnt/sysroot/usr ...`），修完卸载重启回正常系统。
- `/proc` `/sys` 若被改：**重启自动复位**，或 `chmod 555 /proc /sys`（报错忽略，内核管理）。
- 验证：`ls -ld / /usr /usr/bin /etc /home /tmp /root /dev`（应 `drwxr-xr-x root root`，/tmp 为 `drwxrwxrwt`），`systemctl status sshd`，再从本机 `ssh` 测登录；SSH 通了再用普通用户 + sudo 收尾剩余目录。
- 损坏与修复**均非递归**（无 -R），目录内文件内容/属主未受影响；`/` 本身未被动；SELinux 标签不受 chmod/chown 影响，无需 restorecon。
**预防**: ① 不给简单任务叠加它不需要的步骤：本例「下线服务」根本不需要 chown/chmod 备份文件；备份直接放当前用户自己可写的目录、不用 sudo cp 制造 root 属主文件，从源头消除「补救」需求。② 破坏性命令（尤其叠 sudo + 通配符 /*）前显式校验变量非空（`[ -n "$VAR" ]` / `${VAR:?}`），绝不在 sudo/glob 里用可能为空的变量，执行前先 echo 预演展开。③ `set -e` 脚本警惕「中断点跳过了后续命令依赖的赋值」。
**标签**: shell, sudo, chmod, chown, 空变量, 通配符, glob, set -e, 过度设计, 自造问题再补救, 权限恢复, dac_override, ssh无法登录, 运维事故, 恢复runbook
