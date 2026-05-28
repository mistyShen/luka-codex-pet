# Next Steps

当前权威 run 目录：

```text
/Users/a1234/Documents/coding/luka_pet/runs/luka-codex
```

## 1. 生成 base

读取：

```text
runs/luka-codex/prompts/base-pet.md
```

生成一张单体全身 Q 版巡音流歌 Codex 宠物图，纯 `#00FF00` 背景。选好输出图后执行：

```bash
./scripts/mark_job_complete.sh base /absolute/path/to/selected-base.png
```

这会同时创建：

```text
runs/luka-codex/references/canonical-base.png
```

## 2. 生成动作 row

base 完成后，查看未完成 job：

```bash
jq '.jobs[] | select(.status != "complete") | {id, depends_on, prompt_file, input_images, output_path}' runs/luka-codex/imagegen-jobs.json
```

每个 row 使用对应 prompt 和 manifest 中列出的 input images。选好输出图后：

```bash
./scripts/mark_job_complete.sh idle /absolute/path/to/idle-row.png
./scripts/mark_job_complete.sh running-right /absolute/path/to/running-right-row.png
```

`running-left` 可以在 `running-right` 视觉稳定时镜像派生：

```bash
./scripts/derive_running_left.sh
```

如果镜像会让耳机、麦克风、小章鱼或手持道具方向不自然，就单独生成 `running-left` 并用 `mark_job_complete.sh` 标记。

## 3. 抽帧、验证、打包

所有 job 都完成后执行：

```bash
./scripts/process_and_package.sh
```

成功后会生成：

```text
runs/luka-codex/final/spritesheet.webp
runs/luka-codex/final/validation.json
runs/luka-codex/qa/contact-sheet.png
runs/luka-codex/qa/previews/
package/pet.json
package/spritesheet.webp
${CODEX_HOME:-$HOME/.codex}/pets/luka-codex/
```
