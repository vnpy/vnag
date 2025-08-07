from pathlib import Path
import markdown
import time
from datetime import datetime

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

            # 自动清理30天前已删除的会话
            self.gateway.cleanup_deleted_sessions()

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

        # API Key 使用密码框
        self.config_api_key = QtWidgets.QLineEdit(self.api_key)
        self.config_api_key.setEchoMode(QtWidgets.QLineEdit.EchoMode.Password)

        # 添加显示/隐藏按钮
        api_key_layout = QtWidgets.QHBoxLayout()
        api_key_layout.setContentsMargins(0, 0, 0, 0)
        api_key_layout.addWidget(self.config_api_key)

        toggle_visibility_button = QtWidgets.QPushButton("显示")
        toggle_visibility_button.setFixedWidth(40)
        toggle_visibility_button.setToolTip("显示/隐藏 API Key")
        toggle_visibility_button.clicked.connect(self._toggle_api_key_visibility)
        api_key_layout.addWidget(toggle_visibility_button)

        self.config_model_name = QtWidgets.QLineEdit(self.model_name)
        self.config_max_tokens = QtWidgets.QLineEdit(
            str(self.max_tokens) if self.max_tokens else ""
        )
        self.config_temperature = QtWidgets.QLineEdit(
            str(self.temperature) if self.temperature else ""
        )

        # 添加到表单
        config_form.addRow("服务地址:", self.config_base_url)
        config_form.addRow("API Key:", api_key_layout)
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

        # 移除Stream开关

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

        # 文件显示区域（使用滚动区域）
        self.file_display_area = QtWidgets.QScrollArea()
        self.file_display_area.setWidgetResizable(True)
        self.file_display_area.setMaximumHeight(40)
        self.file_display_area.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        
        # 内容容器
        self.file_display_container = QtWidgets.QWidget()
        self.file_display_layout = QtWidgets.QVBoxLayout(self.file_display_container)
        self.file_display_layout.setContentsMargins(0, 0, 0, 0)
        self.file_display_layout.setSpacing(2)
        self.file_display_layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop)
        
        self.file_display_area.setWidget(self.file_display_container)
        self.file_display_area.setVisible(False)  # 初始隐藏

        # 组装输入区域
        input_layout.addLayout(input_top_layout)
        input_layout.addWidget(self.file_display_area)  # 添加文件显示区域
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

            # 统一格式：User标题和内容都使用相同的行距
            user_html = (
                f'<div style="margin-bottom: 20px; display: block;">'
                f'<div style="margin-bottom: 10px; font-weight: bold;">💬 User</div>'
                f'<div style="margin-bottom: 10px;">{escaped_content}</div>'
                f'</div>'
            )
            self.history_widget.insertHtml(user_html)
            # 确保消息之间有换行
            self.history_widget.insertPlainText('\n')
        elif role == "assistant":
            # AI返回内容以Markdown渲染
            html_content = markdown.markdown(
                content,
                extensions=['fenced_code', 'codehilite']
            )

            # 统一格式：Assistant标题和内容都使用相同的行距
            assistant_html = (
                f'<div style="margin-bottom: 20px; display: block;">'
                f'<div style="margin-bottom: 10px; font-weight: bold;">✨ Assistant</div>'
                f'<div style="margin-bottom: 10px;">{html_content}</div>'
                f'</div>'
            )
            self.history_widget.insertHtml(assistant_html)
            # 确保消息之间有换行
            self.history_widget.insertPlainText('\n')

        # 确保滚动条滚动到最新消息
        self.history_widget.moveCursor(QtGui.QTextCursor.MoveOperation.End)

    def init_menu(self) -> None:
        """初始化菜单"""
        menu_bar: QtWidgets.QMenuBar = self.menuBar()

        sys_menu: QtWidgets.QMenu = menu_bar.addMenu("系统")
        sys_menu.addAction("退出", self.close)

        session_menu: QtWidgets.QMenu = menu_bar.addMenu("会话")
        session_menu.addAction("新建会话", self.new_session)
        session_menu.addAction("回收站", self.show_trash)

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
        # 所有对话都使用流式输出
        use_stream = True

        # 添加用户消息到历史
        self.append_message("user", text)

        # 添加用户消息到gateway的聊天历史
        user_message = {"role": "user", "content": text}
        self.gateway.chat_history.append(user_message)

        # 流式输出模式 (现在所有对话都是流式的)
        try:
            # 获取流式响应
            stream = self.gateway.invoke_streaming(
                messages=self.gateway.get_chat_history(),
                use_rag=use_rag,
                user_files=user_files
            )

            # 添加空的助手消息到聊天历史，用于后续更新
            assistant_message = {"role": "assistant", "content": ""}
            self.gateway.chat_history.append(assistant_message)

            # 简化流式输出：直接使用append_message的格式
            full_content = ""
            
            # 创建缓冲区，减少UI更新频率
            chunk_buffer = ""
            update_interval = 0.2  # 200ms更新一次
            buffer_size_threshold = 20  # 缓冲区大小阈值
            last_update_time = time.time()
            
            for chunk in stream:
                # 正常内容处理
                full_content += chunk
                chunk_buffer += chunk
                
                # 控制UI更新频率
                current_time = time.time()
                if (current_time - last_update_time >= update_interval or 
                    len(chunk_buffer) >= buffer_size_threshold or 
                    any(mark in chunk for mark in ["。", ".", "\n", "!", "?", "！", "？"])):
                    
                    # 更新历史记录
                    history = self.gateway.get_chat_history()
                    if history and history[-1]["role"] == "assistant":
                        history[-1]["content"] = full_content

                    # 清空历史显示并重新渲染
                    self.history_widget.clear()
                    for message in self.gateway.get_chat_history():
                        self.append_message(message["role"], message["content"])

                    # 滚动到底部
                    self.history_widget.moveCursor(QtGui.QTextCursor.MoveOperation.End)
                    QtWidgets.QApplication.processEvents()
                    
                    # 重置缓冲区和计时器
                    chunk_buffer = ""
                    last_update_time = current_time
                    time.sleep(0.01)
            
            # 保存会话
            self.gateway._save_session()
            self.status_label.setText("就绪")

        except Exception as e:
            self.status_label.setText(f"流式输出错误: {str(e)}")

        # 流式模式不需要刷新UI，因为已经实时更新了

        # 清理选择的文件
        self.selected_files.clear()
        self._clear_file_display()
        self.file_display_area.setVisible(False)

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
                    current_id = current_item.data(QtCore.Qt.ItemDataRole.UserRole)
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
                updated_at = (session.get('updated_at', '')[:16].replace('T', ' '))

                # 创建列表项
                item = QtWidgets.QListWidgetItem()
                item.setData(QtCore.Qt.ItemDataRole.UserRole, session['id'])
                self.session_list.addItem(item)

                # 创建自定义组件
                widget = QtWidgets.QWidget()
                layout = QtWidgets.QHBoxLayout(widget)
                layout.setContentsMargins(5, 2, 5, 2)

                # 标题标签
                title_label = QtWidgets.QLabel(title)
                title_label.setWordWrap(True)

                # 时间标签
                time_label = QtWidgets.QLabel(updated_at)
                time_label.setStyleSheet("color: gray; font-size: 9pt;")

                # 菜单按钮
                menu_button = QtWidgets.QPushButton("...")
                menu_button.setFixedSize(25, 20)
                menu_button.setStyleSheet("QPushButton { border: none; }")
                menu_button.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)

                # 创建菜单
                menu = QtWidgets.QMenu()
                edit_action = menu.addAction("编辑标题")
                delete_action = menu.addAction("删除会话")
                export_action = menu.addAction("导出会话")

                # 连接菜单项信号
                session_id = session['id']
                edit_action.triggered.connect(lambda checked=False, sid=session_id, t=title: self.edit_session_title(sid, t))
                delete_action.triggered.connect(lambda checked=False, sid=session_id: self.delete_session(sid))
                export_action.triggered.connect(lambda checked=False, sid=session_id, t=title: self.export_session(sid, t))

                # 连接按钮点击事件
                menu_button.clicked.connect(lambda checked=False, m=menu, b=menu_button: m.exec_(b.mapToGlobal(QtCore.QPoint(0, b.height()))))

                # 添加到布局
                right_layout = QtWidgets.QVBoxLayout()
                right_layout.addWidget(time_label, alignment=QtCore.Qt.AlignRight)
                right_layout.addWidget(menu_button, alignment=QtCore.Qt.AlignRight)

                layout.addWidget(title_label, 1)  # 1表示伸展因子
                layout.addLayout(right_layout, 0)  # 0表示不伸展

                # 设置自定义组件
                self.session_list.setItemWidget(item, widget)

                # 调整列表项高度以适应内容
                item.setSizeHint(widget.sizeHint())

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
            # 清空之前的文件显示
            self._clear_file_display()

            self.selected_files = file_paths

            # 为每个文件创建一个小框
            for file_path in file_paths:
                file_name = Path(file_path).name
                if len(file_name) > 20:  # 限制文件名长度
                    display_name = file_name[:17] + "..."
                else:
                    display_name = file_name

                # 创建文件项容器
                file_item = QtWidgets.QFrame()
                file_item.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
                file_item.setStyleSheet("background-color: #3C3C3C; border-radius: 4px; color: white;")
                file_item.setMaximumHeight(22)  # 更小的高度

                # 文件项布局
                item_layout = QtWidgets.QHBoxLayout(file_item)
                item_layout.setContentsMargins(4, 0, 2, 0)
                item_layout.setSpacing(0)

                # 文件名称（不使用图标）
                file_label = QtWidgets.QLabel(display_name)
                file_label.setStyleSheet("color: white;")

                # 关闭按钮
                close_button = QtWidgets.QPushButton("×")
                close_button.setFixedSize(14, 14)
                close_button.setStyleSheet("QPushButton { border: none; color: white; font-weight: bold; }")
                close_button.clicked.connect(lambda checked=False, fp=file_path: self._remove_file(fp))

                # 添加到布局
                item_layout.addWidget(file_label)
                item_layout.addWidget(close_button)

                # 添加到文件显示区域
                self.file_display_layout.addWidget(file_item)

            # 显示文件区域
            self.file_display_area.setVisible(True)

            # 显示简短提示
            self.status_label.setText(f"已选择 {len(file_paths)} 个文件")

    def _remove_file(self, file_path: str) -> None:
        """移除选择的文件"""
        # 从已选文件列表中移除
        if file_path in self.selected_files:
            self.selected_files.remove(file_path)

        # 重新构建文件显示区域
        self._clear_file_display()

        # 如果还有文件，重新显示
        if self.selected_files:
            for fp in self.selected_files:
                file_name = Path(fp).name
                if len(file_name) > 20:
                    display_name = file_name[:17] + "..."
                else:
                    display_name = file_name

                # 创建文件项容器
                file_item = QtWidgets.QFrame()
                file_item.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
                file_item.setStyleSheet("background-color: #3C3C3C; border-radius: 4px; color: white;")
                file_item.setMaximumHeight(22)  # 更小的高度

                # 文件项布局
                item_layout = QtWidgets.QHBoxLayout(file_item)
                item_layout.setContentsMargins(4, 0, 2, 0)
                item_layout.setSpacing(0)

                # 文件名称（不使用图标）
                file_label = QtWidgets.QLabel(display_name)
                file_label.setStyleSheet("color: white;")

                # 关闭按钮
                close_button = QtWidgets.QPushButton("×")
                close_button.setFixedSize(14, 14)
                close_button.setStyleSheet("QPushButton { border: none; color: white; font-weight: bold; }")
                close_button.clicked.connect(lambda checked=False, fp=fp: self._remove_file(fp))

                # 添加到布局
                item_layout.addWidget(file_label)
                item_layout.addWidget(close_button)

                # 添加到文件显示区域
                self.file_display_layout.addWidget(file_item)

            self.status_label.setText(f"已选择 {len(self.selected_files)} 个文件")
        else:
            self.file_display_area.setVisible(False)
            self.status_label.setText("就绪")

    def _clear_file_display(self) -> None:
        """清空文件显示区域"""
        # 清除所有子控件
        while self.file_display_layout.count():
            item = self.file_display_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def new_session(self) -> None:
        """新建会话"""
        self.gateway.new_session()
        self.load_history()
        self.status_label.setText("已创建新会话")

    def show_sessions(self) -> None:
        """显示会话列表（切换到会话标签页）"""
        # 切换到会话标签页
        self.tab_widget.setCurrentIndex(0)

        # 刷新会话列表
        self.refresh_session_list()

    # 移除toggle_stream_mode方法，因为我们现在总是使用流式输出

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

    def show_trash(self) -> None:
        """显示回收站（已删除的会话）"""
        # 获取已删除会话
        deleted_sessions = self.gateway.get_deleted_sessions()

        if not deleted_sessions:
            QtWidgets.QMessageBox.information(self, "回收站", "回收站为空")
            return

        dialog = TrashDialog(deleted_sessions, self.gateway, self)
        if dialog.exec_():
            self.refresh_session_list()

    def edit_session_title(self, session_id: str, current_title: str) -> None:
        """编辑会话标题"""
        new_title, ok = QtWidgets.QInputDialog.getText(
            self,
            "编辑标题",
            "请输入新标题:",
            QtWidgets.QLineEdit.Normal,
            current_title
        )

        if ok and new_title and new_title != current_title:
            # 更新标题
            if self.gateway._session_manager.update_session_title(session_id, new_title):
                # 刷新会话列表
                self.refresh_session_list()

    def delete_session(self, session_id: str) -> None:
        """删除会话"""
        reply = QtWidgets.QMessageBox.question(
            self, "确认删除", "确定要删除这个会话吗？",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
        )
        
        if reply == QtWidgets.QMessageBox.StandardButton.Yes:
            # 检查是否是当前会话
            is_current = self.gateway._session_manager.current_session_id == session_id
            
            if self.gateway.delete_session(session_id):
                # 刷新会话列表
                self.refresh_session_list()
                
                # 如果删除的是当前会话，则清空历史显示
                if is_current:
                    self.history_widget.clear()
                    self.status_label.setText("请从左侧选择一个会话或创建新会话")
                
                QtWidgets.QMessageBox.information(self, "成功", "会话已删除")

    def export_session(self, session_id: str, title: str) -> None:
        """导出会话"""
        title, messages = self.gateway.export_session(session_id)

        if not messages:
            QtWidgets.QMessageBox.information(self, "导出会话", "会话为空或不存在")
            return

        # 选择保存路径
        file_path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "导出会话",
            f"{title}.md",
            "Markdown文件 (*.md)"
        )

        if not file_path:
            return

        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                # 写入标题
                f.write(f"# {title}\n\n")

                # 写入时间戳
                f.write(f"导出时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

                # 写入消息
                for msg in messages:
                    role = "用户" if msg['role'] == 'user' else "助手"
                    timestamp = msg.get('timestamp', '').replace('T', ' ')[:16]

                    f.write(f"## {role} ({timestamp})\n\n")
                    f.write(f"{msg['content']}\n\n")

            QtWidgets.QMessageBox.information(self, "导出会话", f"会话已成功导出到: {file_path}")

        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "导出失败", f"导出会话时发生错误: {str(e)}")

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
        dialog = ModelSelectorDialog(self.base_url, self.api_key, self.model_name, self)
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

    def _toggle_api_key_visibility(self) -> None:
        """切换API Key的可见性"""
        sender = self.sender()
        if self.config_api_key.echoMode() == QtWidgets.QLineEdit.EchoMode.Password:
            self.config_api_key.setEchoMode(QtWidgets.QLineEdit.EchoMode.Normal)
            if sender and isinstance(sender, QtWidgets.QPushButton):
                sender.setText("隐藏")
        else:
            self.config_api_key.setEchoMode(QtWidgets.QLineEdit.EchoMode.Password)
            if sender and isinstance(sender, QtWidgets.QPushButton):
                sender.setText("显示")

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


# 移除StreamSwitchButton类，因为我们不再需要流式输出开关


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
        font.setPointSize(8)  # 调大字号
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

    def __init__(self, base_url: str, api_key: str, current_model: str = "", parent=None) -> None:
        """构造函数"""
        super().__init__(parent)

        self.base_url = base_url
        self.api_key = api_key
        self.current_model = current_model
        self.selected_model = ""

        self.init_ui()
        self.load_models()

    def init_ui(self) -> None:
        """初始化UI"""
        self.setWindowTitle("选择模型")
        self.setFixedSize(400, 300)

        # 当前模型显示
        current_model_layout = QtWidgets.QHBoxLayout()
        current_model_layout.addWidget(QtWidgets.QLabel("当前模型:"))

        if self.current_model:
            current_model_label = QtWidgets.QLabel(self.current_model)
            current_model_label.setStyleSheet("color: #FFFFFF;")  # 白色文本
        else:
            current_model_label = QtWidgets.QLabel("未选择")
            current_model_label.setStyleSheet("font-style: italic; color: #999999;")

        current_model_layout.addWidget(current_model_label)
        current_model_layout.addStretch()

        # 搜索框
        self.search_box = QtWidgets.QLineEdit()
        self.search_box.setPlaceholderText("搜索模型...")
        self.search_box.textChanged.connect(self.filter_models)

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
        layout.addLayout(current_model_layout)
        layout.addWidget(self.search_box)
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

            # 应用当前搜索过滤
            self.filter_models(self.search_box.text())

        except Exception as e:
            self.status_label.setText(f"加载模型失败: {str(e)}")

    def filter_models(self, text: str) -> None:
        """根据搜索文本过滤模型列表"""
        for i in range(self.model_list.count()):
            item = self.model_list.item(i)
            if text.lower() in item.text().lower():
                item.setHidden(False)
            else:
                item.setHidden(True)

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

    # 定义信号
    session_deleted = QtCore.Signal(str)  # 参数是被删除的会话ID

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

        export_button = QtWidgets.QPushButton("导出")
        export_button.clicked.connect(self.export_session)
        
        button_layout.addWidget(switch_button)
        button_layout.addWidget(delete_button)
        button_layout.addWidget(export_button)
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

                    # 发出信号通知主窗口刷新会话列表
                    if hasattr(self, "session_deleted") and self.session_deleted is not None:
                        self.session_deleted.emit(session_id)
                else:
                    QtWidgets.QMessageBox.warning(self, "错误", "删除会话失败")
            except RuntimeError:
                QtWidgets.QMessageBox.warning(self, "错误", "会话项已失效，请重新选择")

    def export_session(self) -> None:
        """导出选中的会话"""
        current_item = self.session_list.currentItem()
        if not current_item:
            QtWidgets.QMessageBox.warning(self, "警告", "请选择一个会话")
            return

        session_id = current_item.data(QtCore.Qt.ItemDataRole.UserRole)
        title, messages = self.gateway.export_session(session_id)

        if not messages:
            QtWidgets.QMessageBox.information(self, "导出会话", "选中的会话为空或不存在")
            return

        # 选择保存路径
        file_path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "导出会话",
            f"{title}.md",
            "Markdown文件 (*.md)"
        )

        if not file_path:
            return

        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                # 写入标题
                f.write(f"# {title}\n\n")

                # 写入时间戳
                f.write(f"导出时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

                # 写入消息
                for msg in messages:
                    role = "用户" if msg['role'] == 'user' else "助手"
                    timestamp = msg.get('timestamp', '').replace('T', ' ')[:16]

                    f.write(f"## {role} ({timestamp})\n\n")
                    f.write(f"{msg['content']}\n\n")

            QtWidgets.QMessageBox.information(self, "导出会话", f"会话已成功导出到: {file_path}")

        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "导出失败", f"导出会话时发生错误: {str(e)}")


class TrashDialog(QtWidgets.QDialog):
    """回收站对话框"""

    def __init__(self, deleted_sessions: list[dict], gateway: AgentGateway, parent=None) -> None:
        super().__init__(parent)
        self.deleted_sessions = deleted_sessions
        self.gateway = gateway
        self.init_ui()

    def init_ui(self) -> None:
        self.setWindowTitle("回收站")
        self.setFixedSize(600, 400)

        # 会话列表
        self.session_list = QtWidgets.QListWidget()
        for session in self.deleted_sessions:
            title = session.get('title', '未命名会话')
            deleted_at = session.get('updated_at', '')[:16].replace('T', ' ')
            item_text = f"{title} (删除于 {deleted_at})"

            item = QtWidgets.QListWidgetItem(item_text)
            item.setData(QtCore.Qt.ItemDataRole.UserRole, session['id'])
            self.session_list.addItem(item)

        # 按钮
        button_layout = QtWidgets.QHBoxLayout()

        restore_button = QtWidgets.QPushButton("恢复")
        restore_button.clicked.connect(self.restore_session)

        permanent_delete_button = QtWidgets.QPushButton("永久删除")
        permanent_delete_button.clicked.connect(self.permanent_delete)

        cleanup_button = QtWidgets.QPushButton("清理全部")
        cleanup_button.clicked.connect(self.cleanup_all)

        close_button = QtWidgets.QPushButton("关闭")
        close_button.clicked.connect(self.reject)

        button_layout.addWidget(restore_button)
        button_layout.addWidget(permanent_delete_button)
        button_layout.addWidget(cleanup_button)
        button_layout.addStretch()
        button_layout.addWidget(close_button)

        # 主布局
        main_layout = QtWidgets.QVBoxLayout()
        main_layout.addWidget(QtWidgets.QLabel("已删除的会话："))
        main_layout.addWidget(self.session_list)
        main_layout.addLayout(button_layout)

        self.setLayout(main_layout)

    def restore_session(self) -> None:
        """恢复会话"""
        current_item = self.session_list.currentItem()
        if not current_item:
            QtWidgets.QMessageBox.warning(self, "警告", "请选择一个会话")
            return

        try:
            session_id = current_item.data(QtCore.Qt.ItemDataRole.UserRole)
            if self.gateway.restore_session(session_id):
                row = self.session_list.row(current_item)
                self.session_list.takeItem(row)
                QtWidgets.QMessageBox.information(self, "成功", "会话已恢复")

                # 如果列表为空，关闭对话框
                if self.session_list.count() == 0:
                    self.accept()
            else:
                QtWidgets.QMessageBox.warning(self, "错误", "恢复会话失败")
        except RuntimeError:
            QtWidgets.QMessageBox.warning(self, "错误", "会话项已失效，请重新选择")

    def permanent_delete(self) -> None:
        """永久删除会话"""
        current_item = self.session_list.currentItem()
        if not current_item:
            QtWidgets.QMessageBox.warning(self, "警告", "请选择一个会话")
            return

        reply = QtWidgets.QMessageBox.question(
            self, "确认永久删除",
            "确定要永久删除这个会话吗？此操作不可撤销！",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
        )

        if reply == QtWidgets.QMessageBox.StandardButton.Yes:
            try:
                session_id = current_item.data(QtCore.Qt.ItemDataRole.UserRole)
                # 直接调用内部方法进行永久删除
                if self.gateway._session_manager._permanent_delete_session(session_id):
                    row = self.session_list.row(current_item)
                    self.session_list.takeItem(row)
                    QtWidgets.QMessageBox.information(self, "成功", "会话已永久删除")

                    # 如果列表为空，关闭对话框
                    if self.session_list.count() == 0:
                        self.accept()
                else:
                    QtWidgets.QMessageBox.warning(self, "错误", "永久删除会话失败")
            except RuntimeError:
                QtWidgets.QMessageBox.warning(self, "错误", "会话项已失效，请重新选择")

    def cleanup_all(self) -> None:
        """清理所有已删除的会话"""
        reply = QtWidgets.QMessageBox.question(
            self, "确认清理",
            "确定要清理所有已删除的会话吗？此操作不可撤销！",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
        )

        if reply == QtWidgets.QMessageBox.StandardButton.Yes:
            # 清理所有超过30天的已删除会话
            count = self.gateway.cleanup_deleted_sessions()
            if count > 0:
                QtWidgets.QMessageBox.information(self, "成功", f"已清理 {count} 个会话")
                self.accept()
            else:
                QtWidgets.QMessageBox.information(self, "提示", "没有可清理的会话")
