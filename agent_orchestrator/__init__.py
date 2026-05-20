import pathlib, sys
_this_dir = pathlib.Path(__file__).parent
_hyphen_dir = _this_dir.parent / "agent-orchestrator"
if _hyphen_dir.is_dir():
    __path__.append(str(_hyphen_dir))
