# 验收清单（可直接当交付验收表）

逐项执行 → 记录实测回显 → 打勾。**只认回显，不认"我觉得配好了"。**

| # | 技术点 | 验收命令 | 通过判据 | 实测结果 |
|---|---|---|---|---|
| 1 | VLAN / Trunk | `display port vlan` | Trunk 口 allow-pass 列表与规划一致；Access 口 PVID 正确 | |
| 2 | 链路互通 | `ping -c 4 <对端网关>` | 4 发 4 收，0% 丢包 | |
| 3 | RSTP | `display stp brief` | 根桥角色 ROOT，接入侧为 DESIGNATED/EDGE；无异常 ALTE | |
| 4 | RSTP 收敛 | `display stp root` | 全网根桥一致（主根/备根符合规划） | |
| 5 | Eth-Trunk | `display eth-trunk 1` | 成员口 Selected、Operate up；`Number Of Up Port In Trunk: 2` | |
| 6 | 聚合断链 | 关一个成员口后 `display eth-trunk 1` | 仍为 1/2 UP，业务 ping 不中断 | |
| 7 | 端口镜像 | `display port-mirroring` | 观察口与源口方向（both/inbound/outbound）正确 | |
| 8 | OSPF 邻居 | `display ospf peer brief` | 全部邻居 State = Full | |
| 9 | OSPF 多区域 | `display ospf lsdb` | 有 Type-3 汇总 LSA；ABR 上 `display ospf abr-asbr` 正常 | |
| 10 | OSPF 路由 | `display ip routing-table protocol ospf` | 目标网段存在且下一跳正确 | |
| 11 | BGP 邻居 | `display bgp peer` | State = Established，Up/Down 时长稳定 | |
| 12 | BGP 路由 | `display bgp routing-table` | 本地宣告网段与对端网段齐全，`*>i` / `*>e` 标记正确 | |
| 13 | 路由重分发 | 两侧 `display ip routing-table` | OSPF 域能看到 BGP 网段，BGP 域能看到 OSPF 网段，无环路 | |
| 14 | VRRP 状态 | `display vrrp brief` | 一主一备（Master/Backup），virtual IP 一致；`display vrrp` 优先级符合规划 | |
| 15 | VRRP 切换 | 断开 Master 上行/整机，终端连续 `ping -c 40 网关` | 丢包 ≤ 5%，恢复后仍能通 | |
| 16 | 安全区域 | `display zone` | 各接口归属区域正确（含心跳口） | |
| 17 | 域间策略 | `display security-policy rule all` | 允许/拒绝命中计数符合预期 | |
| 18 | 源 NAT | `display nat-policy rule all`（命中计数递增）+ 会话表 | 内网访问公网成功，会话方向 trust→untrust | |
| 19 | 目的 NAT 发布 | 公网侧 `ping <发布地址>` | 通；且 `display firewall session table` 目的地址已被转换为真实服务器地址 | |
| 20 | HRP 双机 | `display hrp state`（两台） | 一台 Role: active (HRP_M)，另一台 standby (HRP_S)，心跳 running | |
| 21 | HRP 切换 | 断开主用（或停主用设备），终端连续 ping | 丢包可接受、TTL 由 255 变 254（说明流量真的切到备机） | |
| 22 | 配置落盘 | `display saved-configuration \| include sysname` | 每台设备都能回出自己名字 | |

## "假通"识别（重点）

| 现象 | 真实情况 | 正确判据 |
|---|---|---|
| ping 通但 TTL = 255 | 目标被本机/接口应答，不是真实业务主机 | TTL 应为 254/126/128 等（经一跳或多跳转发） |
| 目的 NAT 通了但 `HITS = 0` | 命中的是接口地址或默认策略，NAT 规则没生效 | 规则命中计数必须随流量递增 |
| 会话表里查不到记录 | 流量根本没到设备（或走了别的路径） | `display firewall session table verbose` 要能看到对应源/目的 |
| VRRP 显示 Master 但终端不通 | Vlanif 成员口没 up，虚 IP 没生效 | 先确认 `display vlan <id>` 成员口 up，再回看 `display vrrp` |
| 配置"发过了"却没生效 | 命令发到了错误视图（静默报错被忽略） | 每段配置回读，检查关键行是否真的出现在 `display current-configuration` |

## 交付时给客户/老师看什么

1. 全网拓扑图（含设备名与网段）
2. 每项技术的**实测截图**（真机控制台窗口，标题栏设备名 + 命令回显 + 关键数字）
3. 本清单的填写版（哪项通过、哪项有偏差、原因）
4. 配置留档（每台设备 `display current-configuration` 导出）
5. 备份与恢复说明（`.topo` 文件 + saved-configuration 位置）
