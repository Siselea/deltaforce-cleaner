# 三角洲行动 卸载工具 (Delta Force Cleaner)

[English](README.md) · [License: MIT](LICENSE) · [Contributing](CONTRIBUTING.md)

一键彻底清除 **《三角洲行动》** 及其腾讯 **ACE 反作弊 (AntiCheatExpert)** 的完整残留。
本工具的逻辑来自一次真实的、手工完成的完整卸载，把当时逐项排查出的痕迹固化成了可重复执行的程序。

## 它会清理什么

| 类别 | 具体内容 |
|---|---|
| **游戏本体** | 各盘符下的 `Delta Force` / `DeltaForce` / `rail_user_data` 目录（含 19G 级 UE5 缓存） |
| **ACE 反作弊** | `AntiCheatExpert Service/Protection`、`ACE-ADVT`、`ACE-BOOT`、`ACE-CORE*`、`ACE-GAME`、`ACE-SSC-DRV64` 等服务/驱动 |
| **ACE 文件** | `C:\Program Files\AntiCheatExpert`、`C:\ProgramData\AntiCheatExpert` |
| **注册表** | ACE 卸载项、游戏卸载项、WeGame 主键 |
| **启动器** | `deltaforceminiloader`、`delta_force_launcher` 数据目录、开始菜单快捷方式 |
| **WeGame** | `%APPDATA%\Tencent` 下 WeGame 专属目录（缓存/登录/日志） |

## 它绝不会碰什么

- `filetrace.sys` / `spaceparser.sys` / `spaceport.sys` —— 名字里带 ace 的 **Windows 自带存储驱动**
- `%APPDATA%\Tencent\xwechat`（微信）、`qimei`（微信小程序公共数据）
- QQ 的注册表与 ProgramData 数据

这些误删会直接损坏系统或你正在用的微信/QQ。

## 使用

```
双击  启动.bat          # 图形界面
python main.py          # 等价
```

界面流程：**扫描 → 核对列表（可逐项取消勾选）→ 开始卸载 → 查看日志**。
删除前会弹确认框，且不可撤销。

### 命令行

```bash
python main.py --cli --dry-run     # 只扫描、打印报告，不做任何修改
python main.py --cli --yes         # 扫描并直接执行
python main.py --cli --no-wegame   # 只处理游戏 + ACE
```

## 权限

ACE 是**内核级驱动**，删除服务和系统目录需要管理员权限。
未提权时界面顶部会出现黄色提示条和「以管理员身份重启」按钮。

**卸载完建议重启一次**：驱动文件已删除，但内核模块要到重启后才彻底从内存卸载。

## 安全设计

- **逐项可见可控**：每项都在表格里列出，可单独取消勾选，不存在黑盒全删。
- **试运行**：勾选后执行只模拟、不落盘，方便先看报告。
- **逐项容错**：任何一项失败只记日志，不中断其余项目。
- **探测超时**：全盘目录大小统计带 1.5 秒预算，扫描始终十几秒内返回。

## 结构

```
deltaforce-uninstaller/
├── main.py              入口（GUI / CLI 分发）
├── 启动.bat             双击启动（pythonw 无控制台）
├── app/
│   ├── engine.py        核心：扫描、删除、提权（纯数据进出，可测试）
│   ├── gui.py           Tk 图形界面
│   └── cli.py           命令行封装
└── tests/test_engine.py 冒烟测试
```

## 测试

```bash
python tests/test_engine.py
```
