# Rust 候选：可减少实现工作，尚不能直接准入

检查日期：2026-10-16。这是源码仓库的公开文档、许可文本和 manifest 核查；没有编译、运行、下载人物资产或测量性能。作者的功能与性能声明不记为 Nvwa 的验证结果。

## Humentity：最贴近当前技术栈的候选

固定观察版本：[`286d33124648501535655a0de811cef55152b9fd`](https://github.com/emberlightstudios/Humentity/tree/286d33124648501535655a0de811cef55152b9fd)。根 [LICENSE](https://github.com/emberlightstudios/Humentity/blob/286d33124648501535655a0de811cef55152b9fd/LICENSE) 声明代码可选 MIT 或 Apache-2.0；这不替代其加载的 mesh、targets、衣物和动作的逐项来源核查。

[作者 README](https://github.com/emberlightstudios/Humentity/blob/286d33124648501535655a0de811cef55152b9fd/README.md) 描述了直接读取 MakeHuman 数据、模板形变、随体型拟合骨架、衣物部件和多种动作适配路径。它覆盖的正是“身材变化后不只移动皮肤，还要调整骨架”这个集成问题；这是值得优先验证的设计和代码候选。README 的 crowd 数量、性能及适配能力均未在本机复现，不作为选择理由。

[Cargo.toml](https://github.com/emberlightstudios/Humentity/blob/286d33124648501535655a0de811cef55152b9fd/Cargo.toml) 使用 Bevy `0.19.1`，与 Nvwa 当前根 manifest 的版本相同；这只是减少一个版本障碍，不代表接口、功能开关或 Web 兼容。该 manifest 还包含 `bevy_jolt = { workspace = true, optional = true }`，所读根 manifest 没有对应 workspace 定义；必须在独立目录确认发布包/正确构建方式，不能从 README 示例推定可直接加依赖。

**待证门**：精确版本的最小 native 与 wasm 构建；真实数据加载；一次参数编辑是否同时更新 mesh / rig / inverse bind；没有文件系统和普通线程能力时的浏览器行为；数据与衣物许可；相同 recipe 的 CLI 与图形端结果。第一轮仅一个角色，不引入 crowd、ragdoll 或新物理库。

## OxiHuman：可观察的独立 Rust 路线，当前核心包不足以替代完整角色

固定观察版本：[`603b446854c3d5a9ca478214e7b85008d54786b9`](https://github.com/cool-japan/oxihuman/tree/603b446854c3d5a9ca478214e7b85008d54786b9)。[Cargo.toml](https://github.com/cool-japan/oxihuman/blob/603b446854c3d5a9ca478214e7b85008d54786b9/Cargo.toml) 标记版本 `0.2.1`、Apache-2.0；[作者来源记录](https://github.com/cool-japan/oxihuman/blob/603b446854c3d5a9ca478214e7b85008d54786b9/PROVENANCE.md) 将其代码与 MakeHuman CC0 数据分开。

[README](https://github.com/cool-japan/oxihuman/blob/603b446854c3d5a9ca478214e7b85008d54786b9/README.md) 声明支持 Rust / Wasm、本地参数生成与导出。来源记录同时明确：所带 core pack 只包含基础身体和 38 个形变目标，不带 rig、贴图、衣物、头发或动作。因此不能把“能生成身体、导出 GLB”视为“已具备可捏、可动画的人物系统”。它也明确以写实人体为基础，并不自动覆盖动漫风格。

**待证门**：代码声明与实际行为、包内真实数据及哈希、mesh 与动画骨架结合、更多局部脸部参数、Nvwa 接口成本。作者提供的 clean-room、速度、误差和跨端数字是作者证据，本轮没有独立审计或复算。README 说明部分数据测试会在缺少数据时跳过，故仅取得一次 green suite 也不能证明真实资产通路。

## 对照的意义

MakeHuman/MPFB 的[官方 FAQ](https://static.makehumancommunity.org/mpfb/faq/build_other_chargen.html)明确允许用核心 mesh / targets / system assets 构造新的生成器。这使“复用成熟人体数据，用 Rust 执行”的方向有直接依据。它没有指定必须使用哪一个第三方 Rust 实现，也没有证明这些实现成熟。

MPFB 的[公开维护者答复](https://github.com/makehumancommunity/mpfb2/issues/381#issuecomment-4655951262)建议，面向运行时人物编辑器应考虑直接支持源数据格式，而不是把全部互斥目标塞入 glTF。这个意见支持安排数据驱动路线的对照，不能代替 Nvwa 的工程测量。

**建议**：以成熟 MakeHuman/MPFB 数据为共同参照，先比较“Blender 编译后的人物包 + Nvwa 小参数执行器”与“Humentity 最小数据执行路径”。优先复用已经满足要求的代码；若不满足，记录具体缺口后再补最小部分。不要先重写全套 MakeHuman，也不要因为同为 Rust 就直接绑定尚未验证的框架。

## 方法与限制

- 用 GitHub API 固定两个仓库的观察 commit，并读取上述文本；没有下载大仓库或数据包。
- 按 ctxfs 技能尝试只读挂载两个固定版本。命令持续无输出且挂载目录未出现，已结束本轮两个自有 mount 进程。没有安装系统组件或改变权限。随后仅核查官方仓库公开文本，没有据此声称完成内部算法审计。
- 未读取第三方本地凭据，未启动应用、模型或重编译任务。

**VERIFIED —** 固定版本公开 README、LICENSE、PROVENANCE 和 manifest 已读取；两条 Rust 路线进入候选清单。

**NOT-RUN —** 编译、真实资产、三端功能、视觉品质、性能、clean-room 独立审计和资产再分发准入。
