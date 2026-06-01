"""QQ 音乐相关 MCP 工具（stdio 模式，供 Cursor 等客户端连接）."""
from __future__ import annotations

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("blog-music")



@mcp.tool()
def save_music_track(
    title: str,
    artist: str,
    qq_song_id: int | None = None,
) -> dict[str, str]:
    """保存曲目到博客音乐列表（待接入后端）。"""
    payload: dict[str, str] = {"message": "待实现", "title": title, "artist": artist}
    if qq_song_id is not None:
        payload["qqSongId"] = str(qq_song_id)
    return payload


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
