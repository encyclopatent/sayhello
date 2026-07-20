#!/usr/bin/env python3
"""
MCP server for three-sequence comparison — 让本地agent可以直接调用三序列比对算法。

启动方式（stdio模式，供Claude Code/Desktop连接）：
    python3 compare_mcp.py

在 claude_desktop_config.json 中注册：
    {
        "mcpServers": {
            "compare-sequences": {
                "command": "python3",
                "args": ["/absolute/path/to/compare_mcp.py"],
                "env": {
                    "EMBOSS_ACDROOT": "/opt/anaconda3/envs/rdkit-env/share/EMBOSS/acd/",
                    "EMBOSS_DATA": "/opt/anaconda3/envs/rdkit-env/share/EMBOSS/data/",
                    "PLPLOT_LIB": "/opt/anaconda3/envs/rdkit-env/share/EMBOSS/"
                }
            }
        }
    }
"""

import json
import sys
import os
import uuid
from typing import Any

# 确保可以导入同目录的 compare_utils
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from compare_utils import compare_sequences, batch_compare_from_excel


# ─── MCP 协议工具 ───────────────────────────────────────────

def mcp_send(msg: dict) -> None:
    """按 MCP stdio 协议输出 JSON-RPC 消息"""
    sys.stdout.write(json.dumps(msg, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def mcp_read() -> dict:
    """读取 MCP stdio 输入"""
    line = sys.stdin.readline()
    if not line:
        raise EOFError("stdin closed")
    return json.loads(line)


def serve() -> None:
    """MCP stdio server 主循环"""
    # 发送 server 信息
    mcp_send({
        "jsonrpc": "2.0",
        "method": "server/info",
        "params": {"name": "compare-sequences", "version": "1.0.0"}
    })

    while True:
        try:
            msg = mcp_read()
        except (EOFError, json.JSONDecodeError):
            break

        msg_id = msg.get("id")
        method = msg.get("method", "")
        params = msg.get("params", {})

        if method == "initialize":
            mcp_send({
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {}
                    },
                    "serverInfo": {
                        "name": "compare-sequences",
                        "version": "1.0.0"
                    }
                }
            })

        elif method == "tools/list":
            mcp_send({
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "tools": [
                        {
                            "name": "compare_sequences",
                            "description": "三序列比对与突变分析：以编号序列为坐标系统，比较参比序列与目标序列的同一性和突变位点",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "ref_seq": {
                                        "type": "string",
                                        "description": "参比序列（氨基酸或核酸字符串）"
                                    },
                                    "num_seq": {
                                        "type": "string",
                                        "description": "编号序列（提供坐标系统）"
                                    },
                                    "tgt_seq": {
                                        "type": "string",
                                        "description": "目标序列"
                                    },
                                    "gapopen": {
                                        "type": "number",
                                        "description": "Gap open罚分（默认10.0）",
                                        "default": 10.0
                                    },
                                    "gapextend": {
                                        "type": "number",
                                        "description": "Gap extend罚分（默认0.5）",
                                        "default": 0.5
                                    }
                                },
                                "required": ["ref_seq", "num_seq", "tgt_seq"]
                            }
                        },
                        {
                            "name": "batch_compare",
                            "description": "批量三序列比对：从Excel文件读取多行序列，每行进行三序列比对",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "excel_path": {
                                        "type": "string",
                                        "description": "Excel文件路径，需包含参比序列/reference、编号序列/numbering、目标序列/target列"
                                    },
                                    "gapopen": {
                                        "type": "number",
                                        "description": "Gap open罚分（默认10.0）",
                                        "default": 10.0
                                    },
                                    "gapextend": {
                                        "type": "number",
                                        "description": "Gap extend罚分（默认0.5）",
                                        "default": 0.5
                                    }
                                },
                                "required": ["excel_path"]
                            }
                        }
                    ]
                }
            })

        elif method == "tools/call":
            tool_name = params.get("name", "")
            arguments = params.get("arguments", {})

            try:
                if tool_name == "compare_sequences":
                    result = compare_sequences(
                        ref_seq=arguments["ref_seq"],
                        num_seq=arguments["num_seq"],
                        tgt_seq=arguments["tgt_seq"],
                        gapopen=float(arguments.get("gapopen", 10.0)),
                        gapextend=float(arguments.get("gapextend", 0.5)),
                    )
                    # 只返回关键结果（剔除raw_results等大数据）
                    output = {
                        "identity": f"{result['identity']:.2%}",
                        "longest_identity": f"{result.get('ref_tgt_longest_identity', result['longest_identity']):.2%}",
                        "matches": result['matches'],
                        "mismatches": result['mismatches'],
                        "total_positions": result['total_positions'],
                        "mutations": [
                            f"{m['reference_residue']}{m['numbering_position']}{m['target_residue']}"
                            for m in result['mutations']
                        ],
                        "mutations_detail": result['mutations'],
                        "alignment_chunks": [
                            {
                                "range": f"{chunk['range_start']}-{chunk['range_end']}",
                                "numbering": chunk['numbering'],
                                "reference": chunk['reference'],
                                "target": chunk['target'],
                                "marker": chunk['marker'],
                            }
                            for chunk in result.get('alignment_chunks', [])
                        ],
                    }
                    text = json.dumps(output, ensure_ascii=False, indent=2)

                elif tool_name == "batch_compare":
                    results = batch_compare_from_excel(
                        file_path=arguments["excel_path"],
                        gapopen=float(arguments.get("gapopen", 10.0)),
                        gapextend=float(arguments.get("gapextend", 0.5)),
                    )
                    output = [
                        {
                            "name": r.get("name", f"序列{r.get('index', i+1)}"),
                            "identity": f"{r['identity']:.2%}",
                            "longest_identity": f"{r.get('ref_tgt_longest_identity', r.get('longest_identity', r['identity'])):.2%}",
                            "matches": r['matches'],
                            "mismatches": r['mismatches'],
                            "total_positions": r['total_positions'],
                            "mutations": [
                                f"{m['reference_residue']}{m['numbering_position']}{m['target_residue']}"
                                for m in r['mutations']
                            ],
                        }
                        for i, r in enumerate(results)
                    ]
                    text = json.dumps(output, ensure_ascii=False, indent=2)

                else:
                    mcp_send({
                        "jsonrpc": "2.0",
                        "id": msg_id,
                        "error": {"code": -32601, "message": f"Unknown tool: {tool_name}"}
                    })
                    continue

                mcp_send({
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": text
                            }
                        ]
                    }
                })

            except Exception as e:
                mcp_send({
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "error": {"code": -32000, "message": str(e)}
                })

        elif method == "shutdown":
            break

        else:
            mcp_send({
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {}
            })


if __name__ == "__main__":
    serve()
