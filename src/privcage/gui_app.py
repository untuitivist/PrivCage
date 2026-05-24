from __future__ import annotations

import sys
import secrets
import subprocess
import os
from pathlib import Path

from privcage.config import AppConfig, decode_master_key, load_config
from privcage.encoding import b64url_encode
from privcage.env_status import dependency_statuses, key_status
from privcage.processor import process_input
from privcage.restore import restore_markdown, reveal_placeholder


class GuiState:
    def __init__(self) -> None:
        self.master_key_text = ""
        self.key_id = "gui"
        self.load_saved_key()

    def get_config(self) -> AppConfig:
        if self.master_key_text.strip():
            return AppConfig(master_key=decode_master_key(self.master_key_text.strip()), key_id=self.key_id)
        return load_config()

    @property
    def user_config_path(self) -> Path:
        import os

        appdata = os.environ.get("APPDATA")
        if appdata:
            return Path(appdata) / "PrivCage" / "privcage.key"
        return Path.home() / ".config" / "privcage" / "privcage.key"

    def load_saved_key(self) -> None:
        path = self.user_config_path
        if path.is_file():
            self.master_key_text = path.read_text(encoding="utf-8").strip()


GUI_STATE = GuiState()
TERMINAL_OUTPUT = None


def terminal_log(message: str) -> None:
    global TERMINAL_OUTPUT
    if TERMINAL_OUTPUT is not None:
        TERMINAL_OUTPUT.appendPlainText(message.rstrip())


def run() -> int:
    try:
        from PySide6.QtWidgets import QApplication
    except ImportError as exc:
        print(
            "PySide6 is not available or Qt DLLs failed to load. "
            "Install with `uv pip install -e \".[gui]\"`; on Windows, prefer a clean uv/Python runtime if Anaconda DLLs conflict. "
            f"Details: {exc}",
            file=sys.stderr,
        )
        return 2

    app = QApplication(sys.argv)
    app.setApplicationName("PrivCage")
    window = build_main_window()
    window.resize(1120, 760)
    window.show()
    return app.exec()


def build_main_window():
    from PySide6.QtWidgets import QMainWindow, QTabWidget

    window = QMainWindow()
    window.setWindowTitle("PrivCage")
    tabs = QTabWidget()
    tabs.addTab(build_preprocess_page(), "预处理")
    tabs.addTab(build_bundle_page(), "外发包")
    tabs.addTab(build_restore_page(), "回填恢复")
    tabs.addTab(build_reveal_page(), "占位符查询")
    tabs.addTab(build_terminal_page(), "终端")
    tabs.addTab(build_status_page(), "状态与设置")
    tabs.addTab(build_tutorial_page(), "教程")
    tabs.addTab(build_readme_page(), "README")
    window.setCentralWidget(tabs)
    return window


def build_preprocess_page():
    from PySide6.QtWidgets import (
        QAbstractItemView,
        QCheckBox,
        QHBoxLayout,
        QLabel,
        QLineEdit,
        QPlainTextEdit,
        QPushButton,
        QTableWidget,
        QVBoxLayout,
        QWidget,
    )

    page = QWidget()
    layout = QVBoxLayout(page)
    layout.addWidget(QLabel("生成外网可见 .privacy 和内网 .privcage 状态目录"))

    input_edit = QLineEdit()
    output_edit = QLineEdit()
    layout.addLayout(path_row("输入", input_edit, [("选文件", lambda: pick_file(input_edit)), ("选目录", lambda: pick_dir(input_edit))]))
    layout.addLayout(path_row("输出根目录", output_edit, [("选择", lambda: pick_dir(output_edit))]))

    options = QHBoxLayout()
    centralize_check = QCheckBox("无法处理文件集中到 .privcage/.../unprocessed")
    print_log_check = QCheckBox("显示普通日志")
    run_button = QPushButton("开始预处理")
    options.addWidget(centralize_check)
    options.addWidget(print_log_check)
    options.addStretch()
    options.addWidget(run_button)
    layout.addLayout(options)

    table = QTableWidget(0, 5)
    table.setHorizontalHeaderLabels(["源文件", "状态", "命中", "公开目录", "状态目录"])
    table.setEditTriggers(QAbstractItemView.NoEditTriggers)
    table.horizontalHeader().setStretchLastSection(True)
    layout.addWidget(table)

    log = QPlainTextEdit()
    log.setReadOnly(True)
    log.setMaximumHeight(170)
    layout.addWidget(log)

    def run_preprocess() -> None:
        command = (
            f'privcage preprocess --input "{input_edit.text()}" --output "{output_edit.text()}"'
            f"{' --centralize-unprocessed' if centralize_check.isChecked() else ''}"
            f"{' --print-log' if print_log_check.isChecked() else ''}"
        )
        terminal_log(f"> {command}")
        try:
            config = GUI_STATE.get_config()
            processed, unprocessed = process_input(
                Path(input_edit.text()),
                Path(output_edit.text()),
                config,
                centralize_unprocessed=centralize_check.isChecked(),
            )
        except Exception as exc:  # noqa: BLE001
            show_error(str(exc))
            return

        table.setRowCount(0)
        for item in processed:
            append_row(table, [str(item.source), "processed", str(item.hits), str(item.output_dir), str(item.state_dir)])
            terminal_log(f"processed: {item.source} -> {item.output_dir} ({item.hits} hits)")
        for item in unprocessed:
            append_row(table, [str(item.source), f"unprocessed: {item.reason}", "", "", str(item.destination)])
            log.appendPlainText(
                f"unprocessed: path={item.source} stage={item.stage} reason={item.reason} destination={item.destination}"
            )
            terminal_log(
                f"unprocessed: path={item.source} stage={item.stage} reason={item.reason} destination={item.destination}"
            )
        if print_log_check.isChecked():
            for item in processed:
                log.appendPlainText(f"processed: {item.source} -> {item.output_dir} ({item.hits} hits)")
        show_info(f"完成：成功 {len(processed)}，无法处理 {len(unprocessed)}")

    run_button.clicked.connect(run_preprocess)
    return page


def build_bundle_page():
    from PySide6.QtWidgets import QLabel, QLineEdit, QPlainTextEdit, QPushButton, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget

    page = QWidget()
    layout = QVBoxLayout(page)
    layout.addWidget(QLabel("检查 .privacy 公开目录，确保没有 manifest/index/log 等内网状态文件"))
    privacy_edit = QLineEdit()
    layout.addLayout(path_row(".privacy 目录", privacy_edit, [("选择", lambda: pick_dir(privacy_edit))]))
    scan_button = QPushButton("扫描外发目录")
    layout.addWidget(scan_button)
    tree = QTreeWidget()
    tree.setHeaderLabels(["文件", "状态"])
    layout.addWidget(tree)
    report = QPlainTextEdit()
    report.setReadOnly(True)
    report.setMaximumHeight(150)
    layout.addWidget(report)

    def scan() -> None:
        root = Path(privacy_edit.text())
        tree.clear()
        report.clear()
        if not root.is_dir():
            show_error("请选择有效 .privacy 目录")
            return
        forbidden = {"manifest.json", "process.log", "index.json"}
        problems: list[str] = []
        for path in sorted(root.rglob("*")):
            if path.is_dir():
                continue
            rel = path.relative_to(root).as_posix()
            status = "可外发"
            if path.name in forbidden or "/restore/" in f"/{rel}":
                status = "内部文件混入"
                problems.append(rel)
            tree.addTopLevelItem(QTreeWidgetItem([rel, status]))
        if problems:
            report.appendPlainText("发现内部文件，禁止直接外发：")
            report.appendPlainText("\n".join(problems))
        else:
            report.appendPlainText("检查通过：目录仅包含外网可见文件。")

    scan_button.clicked.connect(scan)
    return page


def build_restore_page():
    from PySide6.QtWidgets import QLabel, QLineEdit, QPlainTextEdit, QPushButton, QVBoxLayout, QWidget

    page = QWidget()
    layout = QVBoxLayout(page)
    layout.addWidget(QLabel("默认输出到 .privacy/{原名}_restored.md，与 document.md 并列"))
    privacy_edit = QLineEdit()
    input_edit = QLineEdit()
    output_edit = QLineEdit()
    layout.addLayout(path_row(".privacy 目录", privacy_edit, [("选择", lambda: pick_dir(privacy_edit))]))
    layout.addLayout(path_row("AI Markdown", input_edit, [("选择", lambda: pick_file(input_edit))]))
    layout.addLayout(path_row("输出 Markdown", output_edit, [("选择", lambda: pick_save_file(output_edit))]))
    run_button = QPushButton("开始回填")
    layout.addWidget(run_button)
    result_box = QPlainTextEdit()
    result_box.setReadOnly(True)
    layout.addWidget(result_box)

    def restore() -> None:
        command = f'privcage restore --privacy "{privacy_edit.text()}" --input "{input_edit.text()}"'
        if output_edit.text().strip():
            command += f' --output "{output_edit.text()}"'
        terminal_log(f"> {command}")
        try:
            config = GUI_STATE.get_config()
            output = Path(output_edit.text()) if output_edit.text().strip() else None
            result = restore_markdown(Path(privacy_edit.text()), Path(input_edit.text()), output, config)
        except Exception as exc:  # noqa: BLE001
            show_error(str(exc))
            return
        message = f"restored: {result.input_path} -> {result.output_path} ({result.restored_count} placeholders)"
        result_box.appendPlainText(message)
        terminal_log(message)

    run_button.clicked.connect(restore)
    return page


def build_reveal_page():
    from PySide6.QtWidgets import QLabel, QLineEdit, QPushButton, QTextEdit, QVBoxLayout, QWidget

    page = QWidget()
    layout = QVBoxLayout(page)
    layout.addWidget(QLabel("查询单个 [PRIVACY:...] 占位符对应明文"))
    privacy_edit = QLineEdit()
    placeholder_edit = QTextEdit()
    result_edit = QTextEdit()
    result_edit.setReadOnly(True)
    layout.addLayout(path_row(".privacy 目录", privacy_edit, [("选择", lambda: pick_dir(privacy_edit))]))
    layout.addWidget(QLabel("完整 placeholder"))
    layout.addWidget(placeholder_edit)
    run_button = QPushButton("查询")
    layout.addWidget(run_button)
    layout.addWidget(QLabel("明文"))
    layout.addWidget(result_edit)

    def reveal() -> None:
        placeholder = placeholder_edit.toPlainText().strip()
        terminal_log(f'> privcage reveal --privacy "{privacy_edit.text()}" --placeholder "{placeholder}"')
        try:
            config = GUI_STATE.get_config()
            value = reveal_placeholder(Path(privacy_edit.text()), placeholder, config)
        except Exception as exc:  # noqa: BLE001
            show_error(str(exc))
            return
        result_edit.setPlainText(value)
        terminal_log(value)

    run_button.clicked.connect(reveal)
    return page


def build_terminal_page():
    from PySide6.QtWidgets import QLabel, QHBoxLayout, QPlainTextEdit, QPushButton, QVBoxLayout, QWidget

    global TERMINAL_OUTPUT
    page = QWidget()
    layout = QVBoxLayout(page)
    layout.addWidget(QLabel("执行 PowerShell 命令，或查看 GUI 操作对应的 CLI 命令与打印结果。"))

    command_edit = QPlainTextEdit()
    command_edit.setPlaceholderText(
        ".venv-gui\\Scripts\\python -m privcage --help\n"
        "$env:PRIVCAGE_MASTER_KEY = \"...\"\n"
        ".venv-gui\\Scripts\\python -m privcage preprocess --input demo_input --output demo_out --print-log"
    )
    command_edit.setMaximumHeight(150)
    layout.addWidget(command_edit)

    buttons = QHBoxLayout()
    run_button = QPushButton("执行")
    clear_button = QPushButton("清空输出")
    help_button = QPushButton("插入 help")
    buttons.addWidget(run_button)
    buttons.addWidget(help_button)
    buttons.addWidget(clear_button)
    buttons.addStretch()
    layout.addLayout(buttons)

    output = QPlainTextEdit()
    output.setReadOnly(True)
    layout.addWidget(output)
    TERMINAL_OUTPUT = output

    def run_command() -> None:
        command = command_edit.toPlainText().strip()
        if not command:
            return
        output.appendPlainText(f"> {command}")
        try:
            completed = subprocess.run(
                ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", command],
                cwd=Path.cwd(),
                capture_output=True,
                text=True,
                check=False,
            )
        except Exception as exc:  # noqa: BLE001
            output.appendPlainText(f"failed to start command: {exc}")
            return
        if completed.stdout:
            output.appendPlainText(completed.stdout.rstrip())
        if completed.stderr:
            output.appendPlainText(completed.stderr.rstrip())
        output.appendPlainText(f"[exit {completed.returncode}]")

    def insert_help() -> None:
        command_edit.setPlainText(".venv-gui\\Scripts\\python -m privcage --help")

    run_button.clicked.connect(run_command)
    help_button.clicked.connect(insert_help)
    clear_button.clicked.connect(output.clear)
    return page


def build_status_page():
    from PySide6.QtWidgets import (
        QAbstractItemView,
        QHBoxLayout,
        QLabel,
        QLineEdit,
        QPlainTextEdit,
        QPushButton,
        QTableWidget,
        QVBoxLayout,
        QWidget,
    )

    page = QWidget()
    layout = QVBoxLayout(page)
    layout.addWidget(QLabel("密钥设置：可直接粘贴 base64url 32-byte 主密钥，或生成本机随机密钥。真实密钥不会显示在状态摘要中。"))

    key_edit = QLineEdit()
    key_edit.setEchoMode(QLineEdit.Password)
    key_edit.setPlaceholderText("base64url encoded 32-byte key")
    key_row = QHBoxLayout()
    key_row.addWidget(QLabel("主密钥"))
    key_row.addWidget(key_edit, 1)
    generate_button = QPushButton("生成随机密钥")
    load_button = QPushButton("从文件加载")
    save_button = QPushButton("保存到用户配置")
    apply_button = QPushButton("应用到本次会话")
    key_row.addWidget(generate_button)
    key_row.addWidget(load_button)
    key_row.addWidget(save_button)
    key_row.addWidget(apply_button)
    layout.addLayout(key_row)

    refresh = QPushButton("刷新状态")
    layout.addWidget(refresh)
    summary = QPlainTextEdit()
    summary.setReadOnly(True)
    summary.setMaximumHeight(130)
    layout.addWidget(summary)
    table = QTableWidget(0, 3)
    table.setHorizontalHeaderLabels(["组件", "状态", "详情"])
    table.setEditTriggers(QAbstractItemView.NoEditTriggers)
    table.horizontalHeader().setStretchLastSection(True)
    layout.addWidget(table)

    def apply_key(show_message: bool = True) -> bool:
        try:
            if key_edit.text().strip():
                decode_master_key(key_edit.text().strip())
            GUI_STATE.master_key_text = key_edit.text().strip()
        except Exception as exc:  # noqa: BLE001
            show_error(str(exc))
            return False
        if show_message:
            show_info("密钥已应用到本次 GUI 会话。")
        reload_status()
        return True

    def generate_key() -> None:
        key_edit.setText(b64url_encode(secrets.token_bytes(32)))
        apply_key(show_message=False)

    def load_key_file() -> None:
        from PySide6.QtWidgets import QFileDialog

        path, _ = QFileDialog.getOpenFileName(page, "选择密钥文件")
        if not path:
            return
        try:
            key_edit.setText(Path(path).read_text(encoding="utf-8").strip())
            apply_key(show_message=False)
        except Exception as exc:  # noqa: BLE001
            show_error(str(exc))

    def save_key_file() -> None:
        if not apply_key(show_message=False):
            return
        if not GUI_STATE.master_key_text:
            show_error("没有可保存的 GUI 主密钥。")
            return
        path = GUI_STATE.user_config_path
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(GUI_STATE.master_key_text + "\n", encoding="utf-8")
        except Exception as exc:  # noqa: BLE001
            show_error(str(exc))
            return
        show_info(f"已保存到：{path}")

    def reload_status() -> None:
        summary.clear()
        gui_key = "GUI session key is set" if GUI_STATE.master_key_text else "GUI session key is not set"
        summary.appendPlainText(f"GUI 密钥状态：{gui_key}")
        summary.appendPlainText(f"环境密钥状态：{key_status()}")
        summary.appendPlainText(f"用户配置路径：{GUI_STATE.user_config_path}")
        summary.appendPlainText("真实密钥不会在界面显示。")
        table.setRowCount(0)
        for item in dependency_statuses():
            append_row(table, [item.name, "可用" if item.available else "缺失", item.detail])

    generate_button.clicked.connect(generate_key)
    load_button.clicked.connect(load_key_file)
    save_button.clicked.connect(save_key_file)
    apply_button.clicked.connect(lambda: apply_key(show_message=True))
    refresh.clicked.connect(reload_status)
    reload_status()
    return page


def build_readme_page():
    from PySide6.QtWidgets import QHBoxLayout, QLabel, QPlainTextEdit, QPushButton, QVBoxLayout, QWidget

    page = QWidget()
    layout = QVBoxLayout(page)
    layout.addWidget(QLabel("用户指南。该版本排除了代码仓库、开发测试和打包细节。"))
    buttons = QHBoxLayout()
    open_pdf_button = QPushButton("打开 PDF")
    reload_button = QPushButton("刷新")
    buttons.addWidget(open_pdf_button)
    buttons.addWidget(reload_button)
    buttons.addStretch()
    layout.addLayout(buttons)
    viewer = QPlainTextEdit()
    viewer.setReadOnly(True)
    layout.addWidget(viewer)

    def guide_path(name: str) -> Path:
        return Path(__file__).resolve().parents[2] / "docs" / name

    def load_guide() -> None:
        path = guide_path("user_guide.md")
        if path.is_file():
            viewer.setPlainText(path.read_text(encoding="utf-8"))
        else:
            viewer.setPlainText(f"找不到用户指南：{path}")

    def open_pdf() -> None:
        path = guide_path("user_guide.pdf")
        if not path.is_file():
            show_error(f"找不到 PDF：{path}")
            return
        os.startfile(path)

    reload_button.clicked.connect(load_guide)
    open_pdf_button.clicked.connect(open_pdf)
    load_guide()
    return page


def build_tutorial_page():
    from PySide6.QtWidgets import QPlainTextEdit, QVBoxLayout, QWidget

    page = QWidget()
    layout = QVBoxLayout(page)
    tutorial = QPlainTextEdit()
    tutorial.setReadOnly(True)
    tutorial.setPlainText(
        """PrivCage 操作教程

核心边界
1. .privacy/ 是外网可见目录，只包含 document.md、{原名}_restored.md、figures/、attachments/。
2. .privcage/ 是内网状态目录，包含 manifest.json、restore/index.json、process.log、无法处理原文件，禁止外发，无需手动操作或选取。
3. {原名}_restored.md 默认与 document.md 并列，保证 ./figures 和 ./attachments 相对引用可用。

GUI 快速流程
1. 打开“状态与设置”。
2. 点击“生成随机密钥”。
3. 如需下次继续使用，点击“保存到用户配置”。
4. 打开“预处理”。
5. 选择输入文件或目录。
6. 选择输出根目录。
7. 可选：勾选“无法处理文件集中到 .privcage/.../unprocessed”。
8. 点击“开始预处理”。
9. 打开“外发包”，选择公开 .privacy 目录，点击“扫描外发目录”。
10. 检查通过后，只把 .privacy 目录中的 document.md、figures/、attachments/ 交给外网 AI。
11. 外网 AI 返回 Markdown 后，打开“回填恢复”。
12. 选择同一个 .privacy 目录。
13. 选择 AI 返回的 Markdown。
14. 输出路径可留空，默认生成 .privacy/{原名}_restored.md。
15. 如需查询单个占位符，打开“占位符查询”，选择 .privacy 目录并粘贴完整 [PRIVACY:...]。

CLI 快速流程
1. 配置测试密钥：
   $env:PRIVCAGE_MASTER_KEY = "NTU1NTU1NTU1NTU1NTU1NTU1NTU1NTU1NTU1NTU1NTU"

2. 预处理：
   .venv-gui\\Scripts\\python -m privcage preprocess --input demo_input --output demo_out --centralize-unprocessed --print-log

3. 外发：
   只发送 demo_out/demo_input.privacy/.../*.privacy/ 下的 document.md、figures/、attachments/。
   不要发送 demo_out/.privcage/。

4. 回填：
   .venv-gui\\Scripts\\python -m privcage restore --privacy demo_out\\demo_input.privacy\\docs\\note.txt.privacy --input ai-result.md --print-log

5. 默认输出：
   demo_out/demo_input.privacy/docs/note.txt.privacy/note.txt_restored.md

6. 查询单个占位符：
   .venv-gui\\Scripts\\python -m privcage reveal --privacy demo_out\\demo_input.privacy\\docs\\note.txt.privacy --placeholder "[PRIVACY:EMAIL:...]"

PDF 规则
1. 文本型 PDF 页面只提取文字，不生成页面图片。
2. 图片型或无文本页面才渲染到 figures/pdf_pages/ 并在 Markdown 中引用。
3. 混合 PDF 按页判断。

常见问题
1. 提示 missing key：去“状态与设置”生成或加载密钥。
2. 外发包检查发现 manifest.json/process.log/index.json：不要外发该目录，说明内部文件混入公开目录。
3. 有 unprocessed：处理结果仍可能部分成功，无法处理文件会在 .privcage/ 下保留并强制打印原因。
"""
    )
    layout.addWidget(tutorial)
    return page


def path_row(label: str, line_edit, buttons: list[tuple[str, object]]):
    from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton

    row = QHBoxLayout()
    row.addWidget(QLabel(label))
    row.addWidget(line_edit, 1)
    for text, callback in buttons:
        button = QPushButton(text)
        button.clicked.connect(callback)
        row.addWidget(button)
    return row


def append_row(table, values: list[str]) -> None:
    from PySide6.QtWidgets import QTableWidgetItem

    row = table.rowCount()
    table.insertRow(row)
    for column, value in enumerate(values):
        table.setItem(row, column, QTableWidgetItem(value))


def pick_file(line_edit) -> None:
    from PySide6.QtWidgets import QFileDialog

    path, _ = QFileDialog.getOpenFileName(None, "选择文件")
    if path:
        line_edit.setText(path)


def pick_save_file(line_edit) -> None:
    from PySide6.QtWidgets import QFileDialog

    path, _ = QFileDialog.getSaveFileName(None, "选择输出文件", filter="Markdown (*.md);;All files (*.*)")
    if path:
        line_edit.setText(path)


def pick_dir(line_edit) -> None:
    from PySide6.QtWidgets import QFileDialog

    path = QFileDialog.getExistingDirectory(None, "选择目录")
    if path:
        line_edit.setText(path)


def show_error(message: str) -> None:
    from PySide6.QtWidgets import QMessageBox

    QMessageBox.critical(None, "PrivCage", message)


def show_info(message: str) -> None:
    from PySide6.QtWidgets import QMessageBox

    QMessageBox.information(None, "PrivCage", message)


if __name__ == "__main__":
    raise SystemExit(run())
