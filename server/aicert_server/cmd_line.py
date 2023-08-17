from typing import Union, List, Any

def format_arg(arg: Any) -> str:
    return f"\"{arg}\""

def format_line(line: Union[str, List[Any]]) -> str:
    return f"{line[0]} {' '.join([format_arg(arg) for arg in line][1:])}" if isinstance(line, list) else line

class CmdLine:
    """Utility class to properly prepare command lines for docker runs
    
    Args:
        *args (Union[str, List[Any]]): each argument represent a single command
            and can either be a string or a list of strings. Elements of the lists
            of strings are automatically surrounded by double quotes in the final
            command line (except the first element which is the command name).
            Individual commands are joined using the `&&` operator in the final
            command line (which makes them functionaly equivalent to a script).
            The whole command line will be wrapped between single quotes and passed
            to the sh shell.
    
    Example usage:
        ```py
        cmd = CmdLine(
            ["mkdir", "test"],
            ["cd", "test"]
        )

        ...
        (
            cmd
            .extend(["echo", "Hello World!"])
            .redirect(["foo"])
        )
        ```

        When cast to a string, this will yield:
        ```bash
        /bin/sh -c 'mkdir "test" && cd "test" && echo "Hello World!" > "foo"'
        ```
    """
    def __init__(self, *args: Union[str, List[Any]], ) -> None:
        self._str: str = ' && '.join([format_line(line) for line in args])
    
    def extend(self, *args: Union[str, List[Any]]) -> None:
        """Extend the command line with more commands joined with the `&&` operator"""
        self._str: str = ' && '.join([self._str, *[format_line(line) for line in args]])
    
    def pipe(self, cmd: Union[str, List[Any]]) -> None:
        """Pipe the commmand line into the provided command"""
        self._str = f"{self._str} | {format_line(cmd)}"
    
    def redirect(self, file: str) -> None:
        """Redirect the commmand line into the specified file"""
        self._str = f"{self._str} > \"{file}\""
    
    def append_to(self, file: str) -> None:
        """Redirect the commmand line at the end of the specified file"""
        self._str = f"{self._str} >> \"{file}\""
    
    def __str__(self) -> str:
        return f"/bin/sh -c '{self._str}'"
