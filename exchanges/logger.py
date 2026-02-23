"""
日志模块 - 优化输出格式
"""

import os
from time_utils import strftime


class Logger:
    LEVELS = {"ERROR": 0, "WARN": 1, "INFO": 2, "DEBUG": 3}
    
    # 颜色代码
    COLORS = {
        "reset": "\033[0m",
        "red": "\033[31m",
        "green": "\033[32m",
        "yellow": "\033[33m",
        "blue": "\033[34m",
        "magenta": "\033[35m",
        "cyan": "\033[36m",
    }
    
    def __init__(self, level: str = "INFO", save_to_file: bool = False, log_file: str = None, 
                 prefix: str = "", color: str = None):
        self.level = self.LEVELS.get(level.upper(), 2)
        self.save_to_file = save_to_file
        self.log_file = log_file
        self.prefix = prefix
        self.color = color
        
        if save_to_file and log_file:
            os.makedirs(os.path.dirname(log_file), exist_ok=True)
    
    def _colorize(self, text: str, color: str = None) -> str:
        """添加颜色"""
        c = color or self.color
        if c and c in self.COLORS:
            return f"{self.COLORS[c]}{text}{self.COLORS['reset']}"
        return text
    
    def _log(self, level: int, icon: str, *args, color: str = None):
        if level <= self.level:
            timestamp = strftime("%H:%M:%S")
            message = " ".join(str(arg) for arg in args)

            if self.prefix:
                line = f"[{timestamp}] {self.prefix} {icon} {message}"
            else:
                line = f"[{timestamp}] {icon} {message}"

            # 控制台输出带颜色
            print(self._colorize(line, color))

            # 文件输出不带颜色
            if self.save_to_file and self.log_file:
                with open(self.log_file, "a", encoding="utf-8") as f:
                    f.write(line + "\n")
    
    def error(self, *args):
        self._log(0, "❌", *args, color="red")
    
    def warn(self, *args):
        self._log(1, "⚠️", *args, color="yellow")
    
    def info(self, *args):
        self._log(2, "ℹ️", *args)
    
    def debug(self, *args):
        self._log(3, "🔍", *args, color="cyan")
    
    def success(self, *args):
        self._log(2, "✅", *args, color="green")
    
    def trade(self, *args):
        self._log(2, "💰", *args, color="magenta")
    
    def divider(self, char: str = "=", length: int = 80):
        print(char * length)
