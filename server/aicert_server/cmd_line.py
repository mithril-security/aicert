from typing import Union, List, Any

class CmdLine:
    def __init__(self, *args: Union[str, List[Any]], ) -> None:
        self._args = args
    
    def extend(self, *args: Union[str, List[Any]]) -> None:
        self._args += args
    
    def __str__(self) -> str:
        def format_arg(arg: Any) -> str:
            return f"\"{arg}\""

        def format_line(line: Union[str, List[Any]]) -> str:
            return f"{line[0]} {' '.join([format_arg(arg) for arg in line][1:])}" if isinstance(line, list) else line
        
        
        return f"/bin/sh -c '{' && '.join([format_line(line) for line in self._args])}'"
