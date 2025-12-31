import os

import logging
import shutil
import json
from typing import Optional, Callable
import asyncio

logger = logging.getLogger(__name__)

class ClaudeClient:
    """封装 Claude Code CLI 的调用逻辑，支持多用户会话管理"""
    
    def __init__(self):
        self.project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.user_sessions = {}


    
    def _format_tool_use(self, tool_name: str, tool_input: dict) -> str:
        """格式化工具调用信息"""
        # 去掉开头的换行，紧凑显示
        tool_msg = f"🛠️ **调用工具**: `{tool_name}`\n"
        
        if isinstance(tool_input, str):
            tool_msg += f"💻 参数: `{tool_input}`\n"
            return tool_msg + "\n"
        
        if 'command' in tool_input:
            cmd = tool_input['command'].strip()
            tool_msg += f"💻 指令: `{cmd}`\n"
        elif 'path' in tool_input:
            path = tool_input['path'].strip()
            tool_msg += f"📂 路径: `{path}`\n"
        elif 'todos' in tool_input:
            todos = tool_input.get('todos', [])
            if todos and isinstance(todos[0], dict):
                content = todos[0].get('content', '').strip()
                tool_msg += f"📝 任务: `{content}`\n"
        
        # 末尾加一个空行
        return tool_msg + "\n"

    def _format_progress(self, progress: dict) -> str:
        """格式化进度信息"""
        if isinstance(progress, str):
            return f"> 🔄 **进度更新**: {progress}\n\n"

        if not isinstance(progress, dict):
            return ""

        content = progress.get('content', '').strip()
        todos = progress.get('todos', [])
        
        # 如果没有具体内容，直接返回
        if not content and not todos:
            return ""
            
        msg = f"> 🔄 **进度更新**: {content}\n"
        
        # 如果有待办列表，展示当前正在做的那一项
        if todos:
            # 找到第一个未完成的任务
            next_task = ""
            for todo in todos:
                if not isinstance(todo, dict):
                    continue
                status = todo.get('status', 'pending')
                if status not in ['completed', 'done']:
                    next_task = todo.get('content', '').strip()
                    break
            
            if next_task and next_task != content:
                 msg += f"> 📋 下一步: {next_task}\n"
        
        # 末尾加一个空行
        return msg + "\n"

    def _process_assistant_content(self, content_list: list) -> str:
        """处理 Assistant 的内容列表 (Text, Thinking, ToolUse)"""
        new_content = ""
        for item in content_list:
            if not isinstance(item, dict):
                continue
            item_type = item.get('type')
            
            if item_type == 'text':
                text = item.get('text', '')
                if text:
                    # 替换掉无效内容
                    cleaned_text = text.replace("(no content)", "").replace("[no content]", "")
                    if cleaned_text:
                        new_content += cleaned_text
            
            elif item_type == 'thinking':
                thinking = item.get('thinking', '')
                if thinking:
                    logger.debug(f"Thinking: {thinking}")

            elif item_type == 'tool_use':
                tool_name = item.get('name', 'Unknown Tool')
                tool_input = item.get('input', {})
                new_content += self._format_tool_use(tool_name, tool_input)
        
        return new_content

    async def run_analysis_streaming(
        self, 
        prompt: str, 
        user_id: int, 
        on_update: Callable[[str], None],
        timeout: int = 600  # 10 分钟
    ) -> Optional[str]:
        """
        流式调用 Claude CLI 执行分析
        :param prompt: 用户指令
        :param user_id: 用户 ID
        :param on_update: 更新回调函数，接收当前累积的输出
        :param timeout: 超时时间 (秒)
        :return: 完整的分析结果文本
        """
        session_uuid = self.user_sessions.get(user_id)
        
        if session_uuid:
            logger.debug(f"🤖 Claude 收到指令（继续会话 {session_uuid}）: {prompt}")
        else:
            logger.debug(f"🤖 Claude 收到指令（新会话）: {prompt}")
        
        process = None
        try:
            # 获取 claude 的完整路径
            claude_path = shutil.which("claude")
            if not claude_path:
                return "⚠️ 系统错误：找不到 Claude CLI"
            
            # 构建命令
            cmd = [claude_path, "-p"]
            
            # 如果有会话 UUID，使用 --resume
            if session_uuid:
                cmd.extend(["--resume", session_uuid])
            
            cmd.extend([
                "--dangerously-skip-permissions",
                "--verbose",  # 实测：stream-json 需要 verbose
                "--output-format", "stream-json",
                prompt
            ])
            
            logger.debug(f"执行命令: {' '.join(cmd)}")
            
            # 启动进程，增加缓冲区限制
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.project_root,
                limit=20 * 1024 * 1024  # 20MB 缓冲区，防止长行被截断
            )
            
            # 实时读取输出
            accumulated_content = ""
            session_id = None
            
            while True:
                try:
                    # 1. 读取第一行（阻塞等待）
                    line = await process.stdout.readline()
                    if not line:
                        break
                        
                    lines_to_process = [line]
                    
                    # 2. 尝试非阻塞读取后续积压的所有行（批量处理）
                    # 这样可以避免 "读一行->回调->读一行->回调" 的低效循环
                    while True:
                        try:
                            # 这里的 timeout=0 实现了非阻塞读取的效果
                            # 如果缓冲区有数据，立即返回；没有数据，抛出 TimeoutError
                            next_line = await asyncio.wait_for(process.stdout.readline(), timeout=0)
                            if not next_line:
                                break
                            lines_to_process.append(next_line)
                        except asyncio.TimeoutError:
                            # 缓冲区已空，开始处理当前批次
                            break
                    
                    # 3. 批量解析处理
                    batch_new_content = ""
                    
                    for line in lines_to_process:
                        try:
                            line_str = line.decode('utf-8-sig').strip()
                            if not line_str:
                                continue
                                
                            data = json.loads(line_str)
                            
                            # 保存 session_id
                            if 'session_id' in data and not session_id:
                                session_id = data['session_id']
                                self.user_sessions[user_id] = session_id
                                logger.debug(f"✅ 会话 ID: {session_id}")
                            
                            event_type = data.get('type')
                            
                            # 1. 处理 AI 回复与动作
                            if event_type == 'assistant':
                                message = data.get('message', {})
                                if isinstance(message, dict):
                                    content_list = message.get('content', [])
                                    if isinstance(content_list, list):
                                        batch_new_content += self._process_assistant_content(content_list)
                            
                            # 2. 处理 User 事件 (Progress / ToolResult)
                            elif event_type == 'user':
                                # 情况 A: 进度更新 (progress 字段)
                                progress = data.get('progress')
                                if progress:
                                    batch_new_content += self._format_progress(progress)
                                
                                # 情况 B: 进度更新 (tool_use_result 里的 newTodos)
                                tool_use_result = data.get('tool_use_result')
                                if isinstance(tool_use_result, dict):
                                    new_todos = tool_use_result.get('newTodos', [])
                                    if new_todos:
                                        # 构造一个伪造的 progress 对象来复用格式化逻辑
                                        fake_progress = {'todos': new_todos, 'content': ''}
                                        # 如果有 activeForm，用它作为 content
                                        if isinstance(new_todos[0], dict) and new_todos[0].get('activeForm'):
                                            fake_progress['content'] = new_todos[0].get('activeForm')
                                        batch_new_content += self._format_progress(fake_progress)

                                # 情况 C: 工具执行结果 (嵌套在 message.content 里)
                                message = data.get('message', {})
                                if isinstance(message, dict):
                                    content_list = message.get('content', [])
                                    if not isinstance(content_list, list):
                                        content_list = []
                                    for item in content_list:
                                        if isinstance(item, dict) and item.get('type') == 'tool_result':
                                        # 检查是否执行出错
                                            is_error = item.get('is_error', False)
                                            if is_error:
                                                batch_new_content += "❌ **工具执行失败**\n\n"
                                            else:
                                                batch_new_content += "✅ **工具执行完成**\n\n"

                            # 3. 处理最终执行结果
                            elif event_type == 'result':
                                final_result = data.get('result', '')
                                logger.debug(f"✅ Claude 执行结束")
                                
                                # 如果累积内容为空，但有最终结果，则使用最终结果
                                if not accumulated_content and final_result:
                                     cleaned_result = final_result.replace("(no content)", "").replace("[no content]", "").strip()
                                     if cleaned_result:
                                         accumulated_content = cleaned_result
                                
                                if not accumulated_content:
                                    accumulated_content = "⚠️ AI 执行完成，但未生成回复。"
                                
                                return accumulated_content

                            elif event_type == 'error':
                                error_data = data.get('error', {})
                                if isinstance(error_data, dict):
                                    error_msg = error_data.get('message', 'Unknown Error')
                                else:
                                    error_msg = str(error_data)
                                logger.error(f"❌ Claude 返回错误: {error_msg}")
                                batch_new_content += f"❌ **系统错误**: {error_msg}\n\n"

                        except json.JSONDecodeError:
                            logger.warning(f"JSON 解析失败: {line[:100]}...")
                            continue
                    
                    # 4. 只有当确实有新内容生成时，才触发回调
                    if batch_new_content:
                        accumulated_content += batch_new_content
                        await on_update(accumulated_content)

                except ValueError as e:
                    logger.warning(f"跳过过长的行: {e}")
                    continue
            
            # 等待进程结束
            await asyncio.wait_for(process.wait(), timeout=timeout)
            
            # 如果没有从 result 获取到内容，返回累积的内容
            if accumulated_content:
                return accumulated_content
                
        except asyncio.TimeoutError:
            logger.error(f"❌ Claude 执行超时 ({timeout}s)")
            return "⚠️ AI 响应超时，请稍后再试。"
        except Exception as e:
            logger.error(f"❌ 调用 Claude 发生异常: {e}")
            return f"⚠️ 系统内部错误: {str(e)}"
        finally:
            # 确保进程被终止，防止僵尸进程
            if process and process.returncode is None:
                try:
                    process.kill()
                    logger.debug("🧹 已清理后台 Claude 进程")
                except Exception as e:
                    logger.warning(f"清理进程失败: {e}")
    
    def clear_session(self, user_id: int):
        """清除用户的会话状态"""
        if user_id in self.user_sessions:
            old_session = self.user_sessions[user_id]
            del self.user_sessions[user_id]
            logger.debug(f"✅ 已清除用户 {user_id} 的会话 {old_session}")
        else:
            logger.debug(f"ℹ️ 用户 {user_id} 没有活跃会话")
