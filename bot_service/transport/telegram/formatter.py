import re
import html

def format_for_telegram(text: str) -> str:
    """
    将 Claude 的 GFM Markdown 转换为 Telegram 支持的 HTML 格式。
    重点解决：
    1. 表格对齐问题（自动检测表格并包裹在 <pre> 中）
    2. 标题加粗
    3. 代码块保留
    4. 基础格式转换 (加粗、斜体、链接)
    """
    if not text:
        return ""

    # 1. 预处理：保护代码块
    # 我们先提取出所有的代码块，避免它们被后续的格式化破坏
    code_blocks = []
    
    def save_code_block(match):
        content = match.group(1) if match.group(1) else match.group(2)
        # 对代码块内容进行 HTML 转义
        escaped_content = html.escape(content)
        code_blocks.append(f"<pre>{escaped_content}</pre>")
        return f"__CODE_BLOCK_{len(code_blocks)-1}__"

    def save_inline_code(match):
        content = match.group(1)
        escaped_content = html.escape(content)
        code_blocks.append(f"<code>{escaped_content}</code>")
        return f"__CODE_BLOCK_{len(code_blocks)-1}__"

    # 替换 ```code``` (支持语言标记)
    text = re.sub(r'```(?:\w+)?\n([\s\S]*?)```', save_code_block, text)
    # 替换 `code`
    text = re.sub(r'`([^`\n]+)`', save_inline_code, text)

    # 2. 处理表格 (这是对齐的关键)
    # 简单的表格检测：连续两行包含 | 且第二行看起来像分隔符 |---|
    def process_tables(text_chunk):
        lines = text_chunk.split('\n')
        new_lines = []
        in_table = False
        table_buffer = []

        for i, line in enumerate(lines):
            # 简单的表格行检测：以 | 开头或结尾，或者包含多个 |
            is_table_row = line.strip().startswith('|') and line.strip().endswith('|')
            
            # 或者是分隔行 |---|
            is_separator = re.match(r'^\s*\|?[\s-]+\|[\s-]+\|.*$', line)
            
            if is_table_row or is_separator:
                if not in_table:
                    # 检查下一行是否是分隔符，或者上一行是否是表头
                    # 这里简化处理：只要看起来像表格行，就开始收集
                    in_table = True
                table_buffer.append(line)
            else:
                if in_table:
                    # 表格结束，处理缓冲区
                    if table_buffer:
                        table_content = '\n'.join(table_buffer)
                        # 将表格包裹在 pre 中以保持对齐
                        new_lines.append(f"<pre>{html.escape(table_content)}</pre>")
                        table_buffer = []
                    in_table = False
                new_lines.append(line)
        
        # 处理文件末尾的表格
        if table_buffer:
            table_content = '\n'.join(table_buffer)
            new_lines.append(f"<pre>{html.escape(table_content)}</pre>")
            
        return '\n'.join(new_lines)

    text = process_tables(text)

    # 3. HTML 转义 (处理普通文本中的 < > &)
    # 注意：此时代码块已经被替换为占位符，表格已经被转义并包裹，
    # 我们只需要转义剩余的普通文本。但是，我们不能简单地全文转义，
    # 因为占位符 __CODE_BLOCK_0__ 不需要转义，而且我们还要插入 HTML 标签。
    
    # 策略：我们将文本按占位符分割，对非占位符部分进行转义和格式化
    parts = re.split(r'(__CODE_BLOCK_\d+__)', text)
    formatted_parts = []
    
    for part in parts:
        if re.match(r'^__CODE_BLOCK_\d+__$', part):
            # 是占位符，直接保留（稍后恢复）
            formatted_parts.append(part)
        else:
            # 是普通文本
            # a. 转义 HTML
            part = html.escape(part)
            
            # b. 处理标题 (# H1 -> <b>H1</b>)
            part = re.sub(r'^#+\s+(.*)$', r'<b>\1</b>', part, flags=re.MULTILINE)
            
            # c. 处理加粗 (**text** -> <b>text</b>)
            part = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', part)
            
            # d. 处理斜体 (*text* -> <i>text</i>) - 慎用，容易误伤列表
            # 只有当 * 两边都不是空格时才视为斜体，或者简单的处理
            # 这里为了安全，暂不处理单星号斜体，除非非常确定，避免把列表项 * item 搞乱
            # Claude 列表通常用 - item，所以 * item 较少见。
            # 尝试匹配 _text_ 作为斜体
            part = re.sub(r'\b_(.*?)_\b', r'<i>\1</i>', part)
            
            # e. 处理链接 [text](url)
            part = re.sub(r'\[(.*?)\]\((.*?)\)', r'<a href="\2">\1</a>', part)
            
            formatted_parts.append(part)
            
    text = ''.join(formatted_parts)

    # 4. 恢复代码块
    def restore_code_block(match):
        idx = int(match.group(1))
        return code_blocks[idx]
    
    text = re.sub(r'__CODE_BLOCK_(\d+)__', restore_code_block, text)

    return text
