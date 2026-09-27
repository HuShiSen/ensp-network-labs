# 华为网络实验与配置模板集（eNSP）

个人实战整理的**通用配置模板 + 验收判据**，覆盖企业网/数据中心常见技术点。全部基于华为 eNSP 仿真环境（S5700/S3700 交换机、AR2240 路由器、USG6000V 防火墙）验证过，可直接套用到同类拓扑。

> 声明：本仓库为**实验室环境的通用配置模板**，示例地址一律使用 RFC1918 私网段（192.168.x / 10.10.x），不含任何客户、项目或生产环境信息。默认口令仅用于实验环境，生产请改用密钥认证与强口令。

---

## 覆盖的技术点

| 编号 | 目录 | 技术点 | 关键验收判据 |
|---|---|---|---|
| 01 | `configs/01_vlan_trunk` | VLAN 划分、Access/Trunk、PVID | `display port vlan` 中 Trunk 口 allow-pass 列表正确 |
| 02 | `configs/02_rstp` | RSTP、根桥主备、边缘端口 | `display stp brief` 角色为 ROOT/DESIGNATED，边缘口为 EDGE |
| 03 | `configs/03_eth_trunk` | Eth-Trunk（LACP 静态） | `display eth-trunk 1` 成员口 Selected 且 `Number Of Up Port In Trunk: 2` |
| 04 | `configs/04_port_mirroring` | 端口镜像（观察口） | `display port-mirroring` 观察口与源口映射正确 |
| 05 | `configs/05_ospf_multi_area` | OSPF 多区域、ABR、开销调整 | `display ospf peer brief` 邻居 Full；`display ospf lsdb` 三类 LSA 齐全 |
| 06 | `configs/06_bgp` | eBGP 邻居、路由宣告与重分发 | `display bgp peer` State = Established；`display bgp routing-table` 有目标网段 |
| 07 | `configs/07_vrrp` | VRRP 主备网关与抢占 | `display vrrp brief` 一主一备，State=Master/Backup，虚 IP 生效 |
| 08 | `configs/08_firewall_zone_nat` | 安全区域、域间策略、源 NAT、目的 NAT 发布 | `display nat-policy rule all` 命中计数递增；会话表方向正确 |
| 09 | `configs/09_hrp_ha` | 防火墙双机热备（HRP）与故障切换 | `display hrp state` Role: active / standby；切换时连续 ping 丢包可接受、TTL 变化 |
| 10 | `configs/10_ipvpn_gre` | IP-VPN（GRE over IPsec 简化版）专线模拟 | `display interface Tunnel0/0/0` UP，协议 GRE/IP；私网互通 |

每个配置文件**头部注释**写明：拓扑假设、地址规划、下发顺序、验收命令与判据（含"看着通其实不通"的假通识别）。

## 速查文档

- [`docs/LAB_TOPOLOGY.md`](docs/LAB_TOPOLOGY.md) —— 建议拓扑与地址规划（可照抄搭环境）
- [`docs/CONVENTIONS.md`](docs/CONVENTIONS.md) —— 命名、接口、地址、VLAN/区域规划约定（多设备统一口径）
- [`docs/VERIFY_CHECKLIST.md`](docs/VERIFY_CHECKLIST.md) —— 逐项验收清单（可直接当交付验收表）
- [`docs/PITFALLS.md`](docs/PITFALLS.md) —— **12 条真实踩坑记录**（eNSP 索引与 CLI 名字不一致、STP 把互联口砍掉、HRP 心跳口必须进安全区、save 被吞回车……）

## 使用方式

```bash
# 1) 按 docs/LAB_TOPOLOGY.md 在 eNSP 里搭好拓扑，设备按 CONVENTIONS 命名
# 2) 逐段下发配置（推荐脚本化，避免手粘出错）
python scripts/push_config.py --host 127.0.0.1 --port 2000 --file configs/01_vlan_trunk/core-switch.txt
# 3) 回读校验（把回显与期望关键字比对，防止"发了但没生效"）
python scripts/verify_output.py --host 127.0.0.1 --port 2000 --check "display port vlan" --expect Trunk
# 4) 逐项打勾 docs/VERIFY_CHECKLIST.md，最后务必 save
```

## 关于 eNSP 的接口索引（最容易踩的坑）

拓扑里的接口索引（idx）**不等于**命令行的接口名，套模板前先确认：

| 设备型号 | CLI 接口名与 idx 的关系 |
|---|---|
| S5700 / S3700 | `GE0/0/(idx+1)` |
| AR2240 | `GE0/0/idx`（idx 0~2） |
| eNSP 通用 Router | `GE0/0/(idx-2)` |
| USG6000V | idx 0 → `GE0/0/0`；idx ≥ 1 → `GE1/0/(idx-1)` |

> 下发前用 `display interface brief` 对一遍，比事后排错快得多。

## License

MIT
