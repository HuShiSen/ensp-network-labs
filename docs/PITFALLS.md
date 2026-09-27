# eNSP 实战踩坑记录（12 条）

都是真金白银踩出来的。写在这里，是为了下次不要在同一个地方再花两小时。

## 1. 拓扑里的接口索引 ≠ 命令行里的接口名

拓扑生成的接口按"索引"排序，但 CLI 名字跟设备型号有关：

| 型号 | CLI 接口名与 idx 关系 |
|---|---|
| S5700 / S3700 | `GE0/0/(idx+1)` |
| AR2240 | `GE0/0/idx`（idx 0~2） |
| eNSP 通用 Router | `GE0/0/(idx-2)` |
| USG6000V | idx 0 → `GE0/0/0`；idx ≥ 1 → `GE1/0/(idx-1)` |

**后果**：把 `GE0/0/1` 的配置写到了 `GE0/0/0` 上，链路怎么都不通。
**做法**：下发前先 `display interface brief` 确认接口清单。

## 2. 单 VLAN 点到点互联口会被 STP 砍成 ALTE

两交换机之间只跑一个 VLAN 的互联口，STP 可能判成冗余路径并阻塞 → 端口状态 ALTE/Discarding。
**做法**：点到点互联口要么跑多个 VLAN，要么明确 `stp disable`（或按规划做根桥与边缘端口设计）。

## 3. USG 的 HRP 心跳口必须加入安全区域

心跳口只配 IP 不加入 zone，HRP 状态会一直异常（不 up）。
**做法**：`firewall zone ha` → `add interface GigabitEthernet1/0/6`（单独建一个 ha 区域最清楚）。

## 4. USG6000V 上没有 `hrp priority`，备机改用 `hrp standby-device`

双机热备主备角色的确认方式与想象不同：
- 主用：正常 `hrp enable` + `hrp interface ... remote <对端IP>`
- 备用：额外加 `hrp standby-device`（设备上不存在 `hrp priority` 这条命令）

**验收**：`display hrp state` 看 Role 是不是 `active (HRP_M)` / `standby (HRP_S)`。

## 5. 控制台下发配置要"先写后读"，`save` 必须一次写入

- 一段配置发完**立刻回读**，否则你无法区分"命令没生效"和"发送时机不对"。
- `save` 与确认要一次性发送：`save\rY\r\r`。分两次发 `y` 会被吞掉回车，表面像在保存，实际没落盘。
- 落盘判据：`display saved-configuration | include sysname`。

## 6. 用命令行/VBoxManage 拉起的虚拟机，eNSP 控制台接不上

这样起来的设备，控制台只回 `#`，且可能抢占主用导致业务 100% 丢包。
**做法**：先 `VBoxManage poweroff` 清掉残留 VM，再在 eNSP 图形界面里右键 → 启动（设备已在运行时点"启动"无效）。接管成功的判据是回显出现 `Username:` 或 `HRP_M<设备名>`。

## 7. 关电脑前必须"文件 → 保存"并正常退出 eNSP

直接关机 = 强制终止虚拟机，未 `save` 的配置全丢，甚至下次打不开拓扑。
**做法**：文件 → 保存 → 退出（让 eNSP 自己关掉全部 VM），再关机。

## 8. 目的 NAT 规则里同时写 zone 条件会与 action 冲突

`destination-zone untrust` 和 `action destination-nat` 混写时，规则能建出来但**没有动作**（回读显示 `(not configure the action)`，HITS 恒为 0），流量落进默认 no-nat。
**做法**：撤掉 zone 条件 + 补 action；同时公网侧接口要 `arp-proxy enable`（否则没人代答发布地址的 ARP）。
**假通判据**：把发布地址配成接口 sub 地址会让 ping"通"，但 TTL=255、HITS=0 —— 那是接口自己在应答，业务没通。

## 9. 破坏性实验后必须回读确认恢复

`shutdown` 成员口做断链演示、断电做切换演示之后，**一定要回读**：
- `display interface GigabitEthernetX | include current state` → UP
- `display eth-trunk 1 | include Operate` → `Number Of Up Port In Trunk: 2`
然后 `save`。脚本"跑完了"不等于设备恢复原状。

## 10. eNSP 里 USG 起得慢，别急着判定失败

USG6000V 启动到可登录常需 1~3 分钟；这期间控制台连接会被拒绝。
**做法**：轮询等待（脚本里等 `Username:` 出现），不要一连接失败就重启设备。

## 11. 内存不足时设备会"随机"挂掉

16G 机器塞 20+ 台设备（尤其含多台 USG6000V）时，会出现设备莫名其妙掉线、控制台无响应。
**做法**：分组启动（核心+防火墙先跑，验证后再起接入/分支），或给系统配足分页文件/换更大内存。

## 12. 抓包验证端口镜像时，观察口要"只收不发"

观察口接了抓包 PC，就不要再拿它跑业务流量；同时确认镜像方向（inbound/outbound/both）与你要抓的流量方向一致，否则会得出"镜像没生效"的错误结论。

---

## 排错顺序（背下来，能省一半时间）

```
① display interface brief        物理/协议状态对不对
② display vlan / port vlan       二层放通了吗
③ display ip routing-table       有路由吗、下一跳对不对
④ display <协议> peer / state     协议邻居起来了吗
⑤ 从两端互 ping + tracert/ping -a  定位断在哪一跳
⑥ 最近一次改动是什么              先回退再分析
```
