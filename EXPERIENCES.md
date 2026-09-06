## 从 Docker 容器通过 SSH 打开主机 RViz2

**日期：** 2026-09-06
**相关模块：** Docker / SSH / ROS 2 Humble / RViz2

**现象：**
容器内执行 `ros2 run rviz2 rviz2` 报 `Package 'rviz2' not found`，但主机已安装 RViz2。容器有 `DISPLAY=:1` 和 X11 socket，也不能直接执行主机程序；在容器 Shell 执行 `exit` 不会得到主机 Shell。

**原因：**
容器和主机的程序安装环境不同。显示接口用于显示窗口，不提供主机命令执行能力。

**解决方法：**
通过 SSH 在主机执行 RViz2，点云与建图仍在容器运行。本次验证的主机用户为 `nvidia`、地址为 `172.26.59.240`、SSH 端口为 `22`、桌面为 `:0`。地址和桌面号变化时需重新确认。

容器专用私钥路径为 `/root/.ssh/elevation_host_rviz`，公钥已加入主机 `~/.ssh/authorized_keys`。私钥不进入仓库。新建容器时需重新配置或安全恢复密钥；只生成不存在的密钥，不覆盖已有密钥：

```bash
ssh-keygen -t ed25519 -f /root/.ssh/elevation_host_rviz -N '' -C elevation-container-rviz
cat /root/.ssh/elevation_host_rviz.pub
```

将公钥整行追加到主机 `~/.ssh/authorized_keys`，主机 `.ssh` 目录权限为 `700`，`authorized_keys` 为 `600`。曾因粘贴的 heredoc 结束标记 `EOF` 前有空格，终端一直显示 `>`，公钥未完成写入；按 Ctrl+C 后用 `printf '%s\n' '公钥整行' >> ~/.ssh/authorized_keys` 完成授权。不要发送私钥或密码。

以下是已实际执行的打开与自动关闭命令（在容器执行）。结束标记 `HOST_SCRIPT` 必须顶格：

```bash
ssh -i /root/.ssh/elevation_host_rviz \
  -o IdentitiesOnly=yes -o BatchMode=yes -o ConnectTimeout=5 \
  -o StrictHostKeyChecking=yes \
  -o UserKnownHostsFile=/tmp/elevation-map-host-known-hosts \
  nvidia@172.26.59.240 'bash -s' <<'HOST_SCRIPT'
source /opt/ros/humble/setup.bash
export DISPLAY=:0
export XDG_RUNTIME_DIR=/run/user/$(id -u)
rviz_log=$(mktemp /tmp/elevation-rviz-test.XXXXXX.log)
printf 'RViz log: %s\n' "$rviz_log"
timeout --signal=INT --kill-after=3s 7s ros2 run rviz2 rviz2 >"$rviz_log" 2>&1
rviz_result=$?
printf 'Launch exit status: %s\n' "$rviz_result"
cat "$rviz_log"
HOST_SCRIPT
```

上述 known-hosts 文件在首次连接时通过 `StrictHostKeyChecking=accept-new` 创建。它位于 `/tmp`，清理后需要重新确认主机指纹并登记，不能假设永久存在。

**验证：**
SSH 返回主机名 `nvidia-desktop`；RViz 日志出现 `OpenGl version: 4.6 (GLSL 4.6)`，确认初始化成功。约 7 秒后发送 SIGINT，等待 3 秒仍未退出，由 timeout 强制终止，退出码为 `137`。随后检查主机进程，没有残留 RViz2。本次验证的是启动与关闭，没有验证地图订阅或截图内容。

**适用范围：**
容器可访问主机 SSH、密钥已授权、主机 Humble/RViz2 和桌面会话可用。本次显示授权已经可用，没有额外修改 X11 授权。

**避免：**
不要把容器 `DISPLAY` 当作主机命令入口；不要将认证失败误判为网络不通；不要用 `pkill rviz2` 关闭用户原有窗口。上述 timeout 仅管理本次启动的进程组。
