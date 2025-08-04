from pathlib import Path
from typing import Any, cast
import markdown

from PySide6 import QtWidgets, QtGui, QtCore

from .gateway import AgentGateway
from .utility import AGENT_DIR, load_json, save_json
from . import __version__


class MainWindow(QtWidgets.QMainWindow):
    """主窗口"""

    def __init__(self) -> None:
        """构造函数"""
        super().__init__()

        # 加载配置
        settings = load_json("gateway_setting.json") or {}
        self.base_url = settings.get("base_url", "")
        self.api_key = settings.get("api_key", "")
        self.model_name = settings.get("model_name", "")
        self.max_tokens = settings.get("max_tokens", "")
        self.temperature = settings.get("temperature", "")

        # 初始化网关
        self.gateway: AgentGateway = AgentGateway()
        if self.base_url and self.api_key and self.model_name:
            self.gateway.init(
                base_url=self.base_url,
                api_key=self.api_key,
                model_name=self.model_name
            )

        self.init_ui()
        self.refresh_display()

    def init_ui(self) -> None:
        """初始化UI"""
        self.setWindowTitle(f"VeighNa Agent - {__version__} - [ {AGENT_DIR} ]")

        self.init_menu()
        self.init_widgets()

    def init_widgets(self) -> None:
        """初始化中央控件"""
        desktop: QtCore.QRect = (
        QtWidgets.QApplication.primaryScreen().availableGeometry()
    )
        
        # 创建主分割布局
        main_splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        
        # ========== 左侧区域 ==========
        left_widget = QtWidgets.QWidget()
        left_layout = QtWidgets.QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        # 创建标签页
        self.tab_widget = QtWidgets.QTabWidget()
        
        # 会话标签页
        self.session_tab = QtWidgets.QWidget()
        session_layout = QtWidgets.QVBoxLayout(self.session_tab)
        
        # 会话列表
        self.session_list = QtWidgets.QListWidget()
        self.session_list.itemClicked.connect(self.on_session_selected)
        
        # 新建会话按钮
        new_session_button = QtWidgets.QPushButton("新建会话")
        new_session_button.clicked.connect(self.new_session)
        
        session_layout.addWidget(self.session_list)
        session_layout.addWidget(new_session_button)
        
        # 配置标签页
        self.config_tab = QtWidgets.QWidget()
        config_layout = QtWidgets.QVBoxLayout(self.config_tab)
        
        # 配置表单
        config_form = QtWidgets.QFormLayout()
        
        # 基础配置项，使用实例属性
        self.config_base_url = QtWidgets.QLineEdit(self.base_url)
        self.config_api_key = QtWidgets.QLineEdit(self.api_key)
        self.config_model_name = QtWidgets.QLineEdit(self.model_name)
        self.config_max_tokens = QtWidgets.QLineEdit(
            str(self.max_tokens) if self.max_tokens else ""
        )
        self.config_temperature = QtWidgets.QLineEdit(
            str(self.temperature) if self.temperature else ""
        )
        
        # 添加到表单
        config_form.addRow("服务地址:", self.config_base_url)
        config_form.addRow("API Key:", self.config_api_key)
        config_form.addRow("模型名称:", self.config_model_name)
        config_form.addRow("最大Token:", self.config_max_tokens)
        config_form.addRow("温度系数:", self.config_temperature)
        
        # 保存按钮
        save_config_button = QtWidgets.QPushButton("保存并应用配置")
        save_config_button.clicked.connect(self.save_config)
        
        config_layout.addLayout(config_form)
        config_layout.addStretch()
        config_layout.addWidget(save_config_button)
        
        # 添加标签页
        self.tab_widget.addTab(self.session_tab, "会话")
        self.tab_widget.addTab(self.config_tab, "配置")
        
        left_layout.addWidget(self.tab_widget)
        
        # ========== 右侧区域 ==========
        right_widget = QtWidgets.QWidget()
        right_layout = QtWidgets.QVBoxLayout(right_widget)
        
        # 历史消息显示区域
        self.history_widget = QtWidgets.QTextEdit()
        self.history_widget.setReadOnly(True)
        
        # 输入区域
        input_container = QtWidgets.QWidget()
        input_layout = QtWidgets.QVBoxLayout(input_container)
        input_layout.setContentsMargins(0, 0, 0, 0)
        
        self.input_widget = QtWidgets.QTextEdit()
        self.input_widget.setMaximumHeight(desktop.height() // 4)
        
        # 输入框上方的控件
        input_top_layout = QtWidgets.QHBoxLayout()
        input_top_layout.addStretch()
        
        # RAG开关
        self.rag_switch = RagSwitchButton()
        self.rag_switch.toggled.connect(self.toggle_rag_mode)
        self.rag_switch.setChecked(True)  # 默认开启
        input_top_layout.addWidget(self.rag_switch)
        
        # 输入框底部的控件
        input_bottom_layout = QtWidgets.QHBoxLayout()
        
        # 文件按钮（使用图标）
        self.file_button = QtWidgets.QPushButton("📎")
        self.file_button.setToolTip("添加文件")
        self.file_button.clicked.connect(self.select_files)
        self.file_button.setFixedSize(30, 30)
        
        # 模型选择按钮
        self.model_button = QtWidgets.QPushButton("@")
        self.model_button.setToolTip("选择模型")
        self.model_button.clicked.connect(self.show_model_selector)
        self.model_button.setFixedSize(30, 30)
        
        # 发送按钮
        self.send_button = QtWidgets.QPushButton("发送")
        self.send_button.clicked.connect(self.send_message)
        self.send_button.setFixedWidth(100)
        
        input_bottom_layout.addWidget(self.file_button)
        input_bottom_layout.addWidget(self.model_button)
        input_bottom_layout.addStretch()
        input_bottom_layout.addWidget(self.send_button)
        
        # 状态标签
        self.status_label = QtWidgets.QLabel("就绪")
        
        # 组装输入区域
        input_layout.addLayout(input_top_layout)
        input_layout.addWidget(self.input_widget)
        input_layout.addLayout(input_bottom_layout)
        
        # 组装右侧布局
        right_layout.addWidget(self.history_widget)
        right_layout.addWidget(input_container)
        right_layout.addWidget(self.status_label)
        
        # 添加到分割器
        main_splitter.addWidget(left_widget)
        main_splitter.addWidget(right_widget)
        
        # 设置初始分割比例
        main_splitter.setSizes([
            int(desktop.width() * 0.3), 
            int(desktop.width() * 0.7)
        ])
        
        # 设置为中央控件
        self.setCentralWidget(main_splitter)
        
        # 初始化其他变量
        self.selected_files = []

    def append_message(self, role: str, content: str) -> None:
        """在会话历史组件中添加消息"""
        self.history_widget.moveCursor(QtGui.QTextCursor.MoveOperation.End)

        if role == "user":
            # 用户内容不需要被渲染
            escaped_content = (content.replace("&", "&amp;")
                             .replace("<", "&lt;")
                             .replace(">", "&gt;")
                             .replace("\n", "<br>"))

            html = f"""
            <p><b>💬 User</b></p>
            <div>{escaped_content}</div>
            <br><br>
            """
            self.history_widget.insertHtml(html)
        elif role == "assistant":
            # AI返回内容以Markdown渲染
            html_content = markdown.markdown(
                content, 
                extensions=['fenced_code', 'codehilite']
            )

            html = f"""
            <p><b>✨ Assistant</b></p>
            {html_content}
            <br><br>
            """
            self.history_widget.insertHtml(html)

        # 确保滚动条滚动到最新消息
        self.history_widget.moveCursor(QtGui.QTextCursor.MoveOperation.End)

    def init_menu(self) -> None:
        """初始化菜单"""
        menu_bar: QtWidgets.QMenuBar = self.menuBar()

        sys_menu: QtWidgets.QMenu = menu_bar.addMenu("系统")
        sys_menu.addAction("退出", self.close)

        session_menu: QtWidgets.QMenu = menu_bar.addMenu("会话")
        session_menu.addAction("新建会话", self.new_session)
        session_menu.addAction("会话列表", self.show_sessions)

        help_menu: QtWidgets.QMenu = menu_bar.addMenu("帮助")
        help_menu.addAction("官网", self.open_website)
        help_menu.addAction("关于", self.show_about)



    def send_message(self) -> None:
        """发送消息（纯UI交互）"""
        text: str = self.input_widget.toPlainText().strip()
        if not text:
            return
        self.input_widget.clear()

        self.status_label.setText("AI服务正在思考中...")
        QtWidgets.QApplication.processEvents()

        # 收集UI状态参数
        use_rag = self.rag_switch.isChecked()
        user_files = self.selected_files if self.selected_files else None

        # 所有业务逻辑都交给gateway处理
        content: str | None = self.gateway.send_message(
            message=text,
            use_rag=use_rag,
            user_files=user_files
        )

        self.status_label.setText("就绪")

        # 刷新UI显示
        self.refresh_display()

        # 清理选择的文件
        self.selected_files.clear()

    def refresh_display(self) -> None:
        """刷新UI显示（从gateway获取数据）"""
        # 从gateway获取对话历史
        chat_history = self.gateway.get_chat_history()
        
        # 更新UI显示
        self.history_widget.clear()
        for message in chat_history:
            self.append_message(message["role"], message["content"])
            
        # 更新会话列表
        self.refresh_session_list()
            
    def refresh_session_list(self) -> None:
        """刷新会话列表"""
        try:
            # 保存当前选中的会话ID
            current_item = self.session_list.currentItem()
            current_id = None
            if current_item:
                try:
                    current_id = current_item.data(
                    QtCore.Qt.ItemDataRole.UserRole
                )
                except RuntimeError:
                    # 如果项已被删除，忽略错误
                    pass
            
            # 清空列表
            self.session_list.clear()
            
            # 获取所有会话
            sessions = self.gateway.get_all_sessions()
            
            # 添加到列表
            for session in sessions:
                title = session.get('title', '未命名会话')
                created_at = (session.get('created_at', '')[:16]
                              .replace('T', ' '))
                item_text = f"{title} ({created_at})"
                
                item = QtWidgets.QListWidgetItem(item_text)
                item.setData(QtCore.Qt.ItemDataRole.UserRole, session['id'])
                self.session_list.addItem(item)
                
                # 如果是当前会话，选中它
                if session['id'] == current_id:
                    self.session_list.setCurrentItem(item)
        except Exception as e:
            # 捕获任何可能的异常，确保UI不会崩溃
            print(f"刷新会话列表时出错: {e}")

    def load_history(self) -> None:
        """加载对话历史"""
        self.gateway.load_history()
        self.refresh_display()

    def clear_history(self) -> None:
        """清空会话历史（UI交互）"""
        i: int = QtWidgets.QMessageBox.question(
            self,
            "清空历史",
            "确定要清空历史吗？",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
        )

        if i == QtWidgets.QMessageBox.StandardButton.Yes:
            # 业务逻辑交给gateway
            self.gateway.clear_history()
            
            # 刷新UI显示
            self.refresh_display()

    def show_about(self) -> None:
        """显示关于"""
        QtWidgets.QMessageBox.information(
            self,
            "关于",
            (
                "VeighNa Agent\n"
                "\n"
                f"版本号：{__version__}\n"
                "\n"
                f"运行目录：{AGENT_DIR}"
            )
        )

    def select_files(self) -> None:
        """选择文件"""
        file_paths, _ = QtWidgets.QFileDialog.getOpenFileNames(
            self,
            "选择要分析的文件",
            "",
            "支持的文档 (*.md *.txt *.pdf *.docx);;所有文件 (*)"
        )
        
        if file_paths:
            self.selected_files = file_paths
            file_names = [Path(fp).name for fp in file_paths]
            # 显示简短提示
            self.status_label.setText(f"已选择 {len(file_names)} 个文件")

    def new_session(self) -> None:
        """新建会话"""
        self.gateway.new_session()
        self.load_history()
        self.status_label.setText("已创建新会话")

    def show_sessions(self) -> None:
        """显示会话列表"""
        sessions = self.gateway.get_all_sessions()
        
        if not sessions:
            QtWidgets.QMessageBox.information(self, "会话列表", "暂无会话记录")
            return
        
        dialog = SessionListDialog(sessions, self.gateway, self)
        if dialog.exec_():
            self.load_history()

    def toggle_rag_mode(self, checked: bool) -> None:
        """切换RAG模式"""
        # 确保 status_label 已经初始化
        if hasattr(self, "status_label"):
            if checked:
                self.status_label.setText("RAG模式已开启")
            else:
                self.status_label.setText("RAG模式已关闭")

    def open_website(self) -> None:
        """打开官网"""
        QtGui.QDesktopServices.openUrl(
            QtCore.QUrl("https://www.github.com/vnpy/vnag")
        )
        
    def show_model_selector(self) -> None:
        """显示模型选择对话框"""
        if not self.base_url or not self.api_key:
            # 如果没有配置API，先打开连接对话框
            QtWidgets.QMessageBox.warning(
                self, 
                "未配置API", 
                "请先在配置标签页中设置API连接信息。"
            )
            self.tab_widget.setCurrentIndex(1)  # 切换到配置标签页
            return
        
        # 创建模型选择对话框
        dialog = ModelSelectorDialog(self.base_url, self.api_key, self)
        if dialog.exec_():
            # 如果用户选择了模型，更新配置表单
            model_name = dialog.selected_model
            if model_name:
                # 只更新配置表单，不更新实例属性或配置文件
                self.config_model_name.setText(model_name)
                
                # 提示用户保存配置
                QtWidgets.QMessageBox.information(
                    self,
                    "模型已选择",
                    f"已选择模型: {model_name}\n请在配置页面点击保存按钮以应用更改。"
                )
                
                # 切换到配置标签页
                self.tab_widget.setCurrentIndex(1)
        
    def on_session_selected(self, item: QtWidgets.QListWidgetItem) -> None:
        """选择会话"""
        try:
            session_id = item.data(QtCore.Qt.ItemDataRole.UserRole)
            session_name = item.text()
            if self.gateway.switch_session(session_id):
                self.load_history()
                self.status_label.setText(f"已切换到会话: {session_name}")
        except RuntimeError:
            # 如果列表项已被删除，则忽略
            pass
            
    def save_config(self) -> None:
        """保存配置并立即应用"""
        # 读取现有配置
        settings = load_json("gateway_setting.json") or {}
        
        # 获取界面输入的配置
        new_base_url = self.config_base_url.text()
        new_api_key = self.config_api_key.text()
        new_model_name = self.config_model_name.text()
        new_max_tokens = self.config_max_tokens.text().strip()
        new_temperature = self.config_temperature.text().strip()
        
        # 更新配置
        settings["base_url"] = new_base_url
        settings["api_key"] = new_api_key
        settings["model_name"] = new_model_name
        
        # 处理可选参数
        if new_max_tokens:
            settings["max_tokens"] = int(new_max_tokens)
        else:
            settings["max_tokens"] = ""
            
        if new_temperature:
            settings["temperature"] = float(new_temperature)
        else:
            settings["temperature"] = ""
            
        # 保存配置
        save_json("gateway_setting.json", settings)
        
        # 更新实例属性
        self.base_url = new_base_url
        self.api_key = new_api_key
        self.model_name = new_model_name
        self.max_tokens = new_max_tokens
        self.temperature = new_temperature
        
        # 如果配置有效，重新初始化网关
        if self.base_url and self.api_key and self.model_name:
            self.gateway.init(
                base_url=self.base_url,
                api_key=self.api_key,
                model_name=self.model_name
            )
            
            QtWidgets.QMessageBox.information(
                self,
                "配置已保存",
                "配置已保存并立即应用。"
            )
        else:
            QtWidgets.QMessageBox.warning(
                self,
                "配置不完整",
                "配置已保存，但API连接信息不完整，无法初始化连接。"
            )


class RagSwitchButton(QtWidgets.QWidget):
    """RAG开关按钮"""
    
    toggled = QtCore.Signal(bool)
    
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setFixedSize(100, 30)  # 调整宽度以容纳更长的文本
        self._checked = False
        
    def setChecked(self, checked: bool) -> None:
        """设置选中状态"""
        if self._checked != checked:
            self._checked = checked
            self.update()
            self.toggled.emit(checked)
    
    def isChecked(self) -> bool:
        """获取选中状态"""
        return self._checked
    
    def mousePressEvent(self, event) -> None:
        """鼠标点击事件"""
        if event.button() == QtCore.Qt.LeftButton:
            self.setChecked(not self._checked)
    
    def paintEvent(self, event) -> None:
        """绘制开关"""
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        
        # 开关背景
        rect = self.rect().adjusted(2, 5, -2, -5)  # 减小上下边距
        radius = rect.height() // 2
        
        if self._checked:
            # 开启状态：绿色背景
            painter.setBrush(QtGui.QBrush(QtGui.QColor(76, 175, 80)))
        else:
            # 关闭状态：灰色背景
            painter.setBrush(QtGui.QBrush(QtGui.QColor(117, 117, 117)))
        
        painter.setPen(QtCore.Qt.NoPen)
        painter.drawRoundedRect(rect, radius, radius)
        
        # 开关圆形按钮
        button_rect = QtCore.QRect()
        button_rect.setSize(QtCore.QSize(rect.height() - 4, rect.height() - 4))
        
        if self._checked:
            # 开启状态：按钮在右侧
            button_rect.moveCenter(QtCore.QPoint(
                rect.right() - radius, rect.center().y()
            ))
        else:
            # 关闭状态：按钮在左侧
            button_rect.moveCenter(QtCore.QPoint(
                rect.left() + radius, rect.center().y()
            ))
        
        painter.setBrush(QtGui.QBrush(QtGui.QColor(255, 255, 255)))
        painter.drawEllipse(button_rect)
        
        # 文字标签
        painter.setPen(QtGui.QColor(255, 255, 255))  # 使用白色文字，更加醒目
        font = painter.font()
        font.setPointSize(8)  # 稍微增大字体
        font.setBold(True)
        painter.setFont(font)
        
        # 直接在开关内部绘制文字
        if self._checked:
            painter.drawText(
                rect, QtCore.Qt.AlignmentFlag.AlignCenter, "RAG ON"
            )
        else:
            painter.drawText(
                rect, QtCore.Qt.AlignmentFlag.AlignCenter, "RAG OFF"
            )





class ModelSelectorDialog(QtWidgets.QDialog):
    """模型选择对话框"""
    
    def __init__(self, base_url: str, api_key: str, parent=None) -> None:
        """构造函数"""
        super().__init__(parent)
        
        self.base_url = base_url
        self.api_key = api_key
        self.selected_model = ""
        
        self.init_ui()
        self.load_models()
        
    def init_ui(self) -> None:
        """初始化UI"""
        self.setWindowTitle("选择模型")
        self.setFixedSize(400, 300)
        
        # 模型列表
        self.model_list = QtWidgets.QListWidget()
        self.model_list.itemDoubleClicked.connect(self.accept)
        
        # 刷新按钮
        refresh_button = QtWidgets.QPushButton("刷新模型列表")
        refresh_button.clicked.connect(self.load_models)
        
        # 确定和取消按钮
        button_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok | 
            QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.on_accept)
        button_box.rejected.connect(self.reject)
        
        # 状态标签
        self.status_label = QtWidgets.QLabel("正在加载模型列表...")
        
        # 布局
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(QtWidgets.QLabel("可用模型:"))
        layout.addWidget(self.model_list)
        layout.addWidget(refresh_button)
        layout.addWidget(self.status_label)
        layout.addWidget(button_box)
        
        self.setLayout(layout)
        
    def load_models(self) -> None:
        """加载模型列表"""
        self.model_list.clear()
        self.status_label.setText("正在加载模型列表...")
        
        try:
            from openai import OpenAI
            client = OpenAI(api_key=self.api_key, base_url=self.base_url)
            models = client.models.list()
            
            model_ids = [model.id for model in models.data]
            model_ids.sort()
            
            for model_id in model_ids:
                self.model_list.addItem(model_id)
                
            self.status_label.setText(f"已加载 {len(model_ids)} 个模型")
            
        except Exception as e:
            self.status_label.setText(f"加载模型失败: {str(e)}")
    
    def on_accept(self) -> None:
        """确认选择"""
        current_item = self.model_list.currentItem()
        if current_item:
            self.selected_model = current_item.text()
            self.accept()
        else:
            QtWidgets.QMessageBox.warning(
                self, 
                "未选择模型", 
                "请选择一个模型。"
            )


class SessionListDialog(QtWidgets.QDialog):
    """会话列表对话框"""

    def __init__(
        self, 
        sessions: list[dict], 
        gateway: AgentGateway, 
        parent=None
    ) -> None:
        """构造函数"""
        super().__init__(parent)
        
        self.sessions = sessions
        self.gateway = gateway
        
        self.init_ui()

    def init_ui(self) -> None:
        """初始化UI"""
        self.setWindowTitle("会话列表")
        self.setFixedSize(600, 400)
        
        # 会话列表
        self.session_list = QtWidgets.QListWidget()
        
        for session in self.sessions:
            title = session.get('title', '未命名会话')
            created_at = session.get('created_at', '')[:16].replace('T', ' ')
            item_text = f"{title} ({created_at})"
            
            item = QtWidgets.QListWidgetItem(item_text)
            item.setData(QtCore.Qt.ItemDataRole.UserRole, session['id'])
            self.session_list.addItem(item)
        
        # 按钮
        button_layout = QtWidgets.QHBoxLayout()
        
        switch_button = QtWidgets.QPushButton("切换")
        switch_button.clicked.connect(self.switch_session)
        
        delete_button = QtWidgets.QPushButton("删除")
        delete_button.clicked.connect(self.delete_session)
        
        close_button = QtWidgets.QPushButton("关闭")
        close_button.clicked.connect(self.reject)
        
        button_layout.addWidget(switch_button)
        button_layout.addWidget(delete_button)
        button_layout.addStretch()
        button_layout.addWidget(close_button)
        
        # 主布局
        main_layout = QtWidgets.QVBoxLayout()
        main_layout.addWidget(QtWidgets.QLabel("选择要切换的会话："))
        main_layout.addWidget(self.session_list)
        main_layout.addLayout(button_layout)
        
        self.setLayout(main_layout)

    def switch_session(self) -> None:
        """切换会话"""
        current_item = self.session_list.currentItem()
        if not current_item:
            QtWidgets.QMessageBox.warning(self, "警告", "请选择一个会话")
            return
        
        try:
            session_id = current_item.data(QtCore.Qt.ItemDataRole.UserRole)
            if self.gateway.switch_session(session_id):
                self.accept()
            else:
                QtWidgets.QMessageBox.warning(self, "错误", "切换会话失败")
        except RuntimeError:
            QtWidgets.QMessageBox.warning(self, "错误", "会话项已失效，请重新选择")

    def delete_session(self) -> None:
        """删除会话"""
        current_item = self.session_list.currentItem()
        if not current_item:
            QtWidgets.QMessageBox.warning(self, "警告", "请选择一个会话")
            return
        
        reply = QtWidgets.QMessageBox.question(
            self, "确认删除", "确定要删除这个会话吗？",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
        )
        
        if reply == QtWidgets.QMessageBox.StandardButton.Yes:
            try:
                session_id = current_item.data(QtCore.Qt.ItemDataRole.UserRole)
                if self.gateway.delete_session(session_id):
                    row = self.session_list.row(current_item)
                    self.session_list.takeItem(row)
                    QtWidgets.QMessageBox.information(self, "成功", "会话已删除")
            except RuntimeError:
                QtWidgets.QMessageBox.warning(self, "错误", "会话项已失效，请重新选择")
