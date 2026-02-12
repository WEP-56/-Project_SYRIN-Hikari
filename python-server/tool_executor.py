"""
智能工具执行模块
让 nanobot 能够自主决定使用哪些工具来完成任务
"""

import json
import asyncio
from typing import Dict, Any, List
from loguru import logger


class ToolExecutor:
    """智能工具执行器 - 让 LLM 决定使用哪些工具"""
    
    def __init__(self, agent, auto_execute: bool = True):
        self.agent = agent
        self.tools = agent.tools if agent else None
        self.provider = agent.provider if agent else None
        self.max_iterations = 10
        self.auto_execute = auto_execute
    
    async def execute_task(self, task: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        执行用户任务，让 LLM 自主决定使用哪些工具
        
        Args:
            task: 用户描述的任务
            context: 额外上下文
            
        Returns:
            执行结果和过程
        """
        if not self.tools or not self.provider:
            return {
                "success": False,
                "error": "Agent not initialized",
                "result": None,
                "thoughts": []
            }
        
        thoughts = []
        iteration = 0
        messages = []
        
        # 构建系统提示
        system_prompt = f"""你是一个智能助手，可以帮助用户执行各种系统任务。

你有以下工具可以使用：
{self._get_tools_description()}

重要说明：
1. 当用户要求"搜索"、"查找"、"查询"信息时，必须使用 web_search 工具获取真实信息
2. 不要使用你的训练数据，必须调用工具获取最新信息
3. 当用户要求"打开"应用时，使用 exec 工具执行打开命令
4. 不要编造链接或信息，必须实际调用工具

请分析用户的任务，决定是否需要使用工具。
如果需要使用工具，请调用相应的工具。
如果不需要工具，直接回答用户。

当前工作目录：{context.get('workspace', '.') if context else '.'}

请用中文回复。"""
        
        messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": f"请帮我完成这个任务：{task}"})
        
        final_result = None
        
        while iteration < self.max_iterations:
            iteration += 1
            
            try:
                # 调用 LLM
                response = await self.provider.chat(
                    messages=messages,
                    tools=self.tools.get_definitions(),
                    model=self.agent.model if self.agent else "gpt-4o-mini"
                )
                
                # 检查是否有工具调用
                if hasattr(response, 'tool_calls') and response.tool_calls:
                    # 执行工具调用
                    tool_results = []
                    
                    for tool_call in response.tool_calls:
                        tool_name = tool_call.function.name
                        tool_args = json.loads(tool_call.function.arguments)
                        
                        thoughts.append(f"调用工具: {tool_name}({tool_args})")
                        logger.info(f"Executing tool: {tool_name} with args: {tool_args}")
                        
                        # 检查执行权限 (auto_execute)
                        # 如果是只读/安全工具，通常允许；如果是高风险工具（如exec, write_file），则检查权限
                        # 目前为了简单，如果 auto_execute=False，则拦截所有工具（除了 web_search 可能安全？）
                        # 细化策略：
                        # - Safe: web_search, read_file, list_dir
                        # - Risky: exec, open_app, write_file, delete_file
                        
                        is_risky = tool_name in ["exec", "write_file", "open_app", "delete_file", "run_script"]
                        
                        if is_risky and not self.auto_execute:
                            error_msg = f"工具 {tool_name} 执行被阻止：自动执行已关闭，且当前未实现手动确认流程。请在设置中开启'自动执行'。"
                            tool_results.append({
                                "tool": tool_name,
                                "error": error_msg,
                                "success": False
                            })
                            thoughts.append(f"工具被阻止: {error_msg}")
                            continue

                        # 执行工具
                        try:
                            result = await self.tools.execute(tool_name, tool_args)
                            tool_results.append({
                                "tool": tool_name,
                                "result": result,
                                "success": True
                            })
                            thoughts.append(f"工具执行成功: {result[:100] if len(str(result)) > 100 else result}")
                        except Exception as e:
                            tool_results.append({
                                "tool": tool_name,
                                "error": str(e),
                                "success": False
                            })
                            thoughts.append(f"工具执行失败: {str(e)}")
                    
                    # 添加工具结果到对话
                    messages.append({
                        "role": "assistant",
                        "content": response.content or "",
                        "tool_calls": [
                            {
                                "id": tc.id,
                                "type": "function",
                                "function": {
                                    "name": tc.function.name,
                                    "arguments": tc.function.arguments
                                }
                            } for tc in response.tool_calls
                        ]
                    })
                    
                    # 添加工具结果
                    for i, tr in enumerate(tool_results):
                        messages.append({
                            "role": "tool",
                            "tool_call_id": response.tool_calls[i].id,
                            "content": tr.get("result", tr.get("error", ""))
                        })
                
                else:
                    # 没有工具调用，直接返回结果
                    final_result = response.content if hasattr(response, 'content') else str(response)
                    thoughts.append(f"任务完成，直接回答: {final_result[:100]}...")
                    break
                    
            except Exception as e:
                logger.error(f"Tool execution error: {e}")
                return {
                    "success": False,
                    "error": str(e),
                    "result": None,
                    "thoughts": thoughts
                }
        
        if final_result is None:
            final_result = "任务执行完成（达到最大迭代次数）"
        
        return {
            "success": True,
            "result": final_result,
            "thoughts": thoughts,
            "iterations": iteration
        }
    
    def _get_tools_description(self) -> str:
        """获取工具描述"""
        descriptions = []
        for name, tool in self.tools._tools.items():
            desc = getattr(tool, 'description', 'No description')
            descriptions.append(f"- {name}: {desc}")
        return "\n".join(descriptions)
    
    async def quick_execute(self, command_type: str, params: Dict[str, Any]) -> str:
        """
        快速执行特定类型的命令（不需要 LLM 决策）
        
        Args:
            command_type: 命令类型（open_app, read_file, write_file, list_dir, exec）
            params: 命令参数
        """
        try:
            # 检查快速执行权限
            is_risky = command_type in ["open_app", "exec", "write_file"]
            if is_risky and not self.auto_execute:
                return "执行被阻止：自动执行已关闭。请在设置中开启'自动执行'以使用此功能。"

            if command_type == "open_app":
                # 打开应用程序
                import subprocess
                import sys
                
                app_name = params.get("app", "")
                if sys.platform == "win32":
                    subprocess.Popen(f"start {app_name}", shell=True)
                    return f"已尝试打开 {app_name}"
                elif sys.platform == "darwin":
                    subprocess.Popen(["open", "-a", app_name])
                    return f"已尝试打开 {app_name}"
                else:
                    subprocess.Popen([app_name])
                    return f"已尝试打开 {app_name}"
            
            elif command_type == "exec":
                # 执行 shell 命令
                import subprocess
                
                cmd = params.get("command", "")
                result = subprocess.run(
                    cmd,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                output = result.stdout if result.returncode == 0 else result.stderr
                return f"命令执行结果:\n{output}"
            
            elif command_type == "read_file":
                # 读取文件
                from pathlib import Path
                
                path = Path(params.get("path", ""))
                if path.exists():
                    content = path.read_text(encoding='utf-8')
                    return f"文件内容:\n{content[:2000]}"  # 限制长度
                else:
                    return f"文件不存在: {path}"
            
            elif command_type == "write_file":
                # 写入文件
                from pathlib import Path
                
                path = Path(params.get("path", ""))
                content = params.get("content", "")
                
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding='utf-8')
                return f"文件已保存: {path}"
            
            elif command_type == "list_dir":
                # 列出目录
                from pathlib import Path
                
                path = Path(params.get("path", "."))
                if path.exists() and path.is_dir():
                    items = list(path.iterdir())
                    result = f"目录 {path} 的内容:\n"
                    for item in items[:20]:  # 限制数量
                        item_type = "📁" if item.is_dir() else "📄"
                        result += f"{item_type} {item.name}\n"
                    if len(items) > 20:
                        result += f"... 还有 {len(items) - 20} 个项目\n"
                    return result
                else:
                    return f"目录不存在: {path}"
            
            else:
                return f"未知的命令类型: {command_type}"
                
        except Exception as e:
            return f"执行失败: {str(e)}"
