from typing import Union, List, Any

def format_arg(arg: Any) -> str:
    return f"\"{arg}\""

def format_line(line: Union[str, List[Any]]) -> str:
    return f"{line[0]} {' '.join([format_arg(arg) for arg in line][1:])}" if isinstance(line, list) else line

class CmdLine:
    def __init__(self, *args: Union[str, List[Any]], ) -> None:
        self._str: str = ' && '.join([format_line(line) for line in args])
    
    def extend(self, *args: Union[str, List[Any]]) -> None:
        self._str: str = ' && '.join([self._str, *[format_line(line) for line in args]])
    
    def pipe(self, cmd: Union[str, List[Any]]) -> None:
        self._str = f"{self._str} | {format_line(cmd)}"
    
    def redirect(self, file: str) -> None:
        self._str = f"{self._str} > \"{file}\""
    
    def append_to(self, file: str) -> None:
        self._str = f"{self._str} >> \"{file}\""
    
    def __str__(self) -> str:
        return f"/bin/sh -c '{self._str}'"
