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

## 2026-08-01 - apt purge 卸载后 update-alternatives 登记不清理，留下自指死链

**现象**: 运行时（如 PHP）全部包 purge 后，`dpkg -l` 干净、进程为零、目录已删，但 `/etc/alternatives/php-fpm.sock` 仍指向已不存在的 `/run/php/php8.1-fpm.sock`，且 `/run/php/php-fpm.sock` 反指 `/etc/alternatives/php-fpm.sock` 形成自指循环。
**根因**: alternatives 登记存放在 `/var/lib/dpkg/alternatives/<group>`（持久化磁盘文件，重启不消失），`apt purge` 只清包文件与 conffiles，部分包的维护脚本不调用 `update-alternatives --remove`，登记与软链就此残留。
**解决**: 判断某运行时是否卸干净，除 `dpkg -l`、进程、目录外，还必须查 `update-alternatives --get-selections`；清理用 `update-alternatives --remove-all <group>`（一并清 dpkg 记录 + `/etc/alternatives` 软链 + 派生链接），再 `rmdir` 空的 `/run/<pkg>`。
**标签**: apt, purge, update-alternatives, 卸载残留, ubuntu, debian

## 2026-08-01 - acme.sh ECC 目录带 _ecc 后缀，据通配符 ls 拼的 rm -rf 静默删空气

**现象**: 清理 acme.sh 证书残留时 `rm -rf ~/.acme.sh/<domain>` 返回 0 看似成功，真实目录纹丝不动。此前用 `ls ~/.acme.sh/<domain>*` 通配符查看，输出的 `.`/`..` 未暴露真实目录名，据此手拼了错误路径。
**根因**: 两层叠加。① acme.sh 的 ECC 证书目录名带 `_ecc` 后缀（`<domain>_ecc/`），通配符 ls 列出的是目录内容而非完整路径；② `rm -rf` 对不存在的路径静默返回 0，路径拼错不会报错。
**解决**: 查 acme.sh 域名目录一律 `ls -la ~/.acme.sh/` 看全名，不用通配符推断路径；删除类操作把 `find <精确路径> -type f` 放在 rm 前面当护栏——路径写错立刻报错暴露。另注意 acme.sh `--remove` 只把 `<domain>.conf` 改名 `.conf.removed`（摘出续期列表），证书/私钥文件仍留在磁盘，清干净须手动删目录。
**标签**: acme.sh, rm -rf, ECC, 通配符, 静默失败, 删除护栏, find

## 2026-08-01 - grep -v "^#" 判断配置/crontab 是否为空时把空行当有效行

**现象**: 脚本用 `crontab -l | grep -qv "^#"` 判断 crontab 是否还有有效任务，纯注释加空行的 crontab 被误判为「含有效任务」，清理逻辑被跳过。
**根因**: `grep -v "^#"` 只排除以 `#` 开头的行；空行与纯空白行不以 `#` 开头，同样命中为「非注释行」。
**解决**: 判空一律用 `grep -vE "^\s*(#|$)"`，同时排除注释行、空行、纯空白行（行首有空白的注释也覆盖到）。
**标签**: grep, crontab, 空行, 判空, shell 脚本
