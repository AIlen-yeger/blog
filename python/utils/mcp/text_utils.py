


def text_from_mcp_result(result) -> str:
    parts:list[str] = []
    for block in getattr(result,"content",[]) or []:
        if getattr(block,"type",None) == "text":
            parts.append(getattr(block,"text",""))

    return "\n".join(p for p in parts if p).strip()