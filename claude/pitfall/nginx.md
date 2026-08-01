# Nginx 踩坑记录

## 2026-08-01 - conf.d 里 .bak-* / .removed-* 历史文件不参与 include 但会被 grep 命中

**现象**: 用 grep 在 `/etc/nginx/conf.d/` 下查某域名/指令的引用，命中一堆结果，误判配置仍在生效；实际命中的全是 `.bak-*`、`.removed-*` 后缀的历史备份文件。
**根因**: nginx 主配置只 `include conf.d/*.conf`，非 `.conf` 后缀的文件根本不加载；但 grep 按内容匹配、不管文件名是否参与 include。另一变体：`sites-enabled/default` 里包自带的注释示例块（如 `fastcgi_pass` 示例）也会被 grep 命中。
**解决**: 核实生效配置一律用 `nginx -T`（输出实际加载的全量配置），要 grep 就对 `nginx -T` 的输出 grep，不直接对目录 grep。
**标签**: nginx, nginx -T, grep, 备份文件, 生效配置核实
