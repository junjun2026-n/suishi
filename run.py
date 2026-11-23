# ============================================================
# 文件名称：run.py
# 生成日期：2026-11-21
# 修改日期：2026-11-21
# 版本信息：v0.261115
# 作者：JUN
# 备注：本程序由AI辅助完成。
# 文件功能用途：启动独立的蜜罐业务服务和管理服务。
# 注意事项：默认绑定所有网卡，业务和管理端口需分别限制访问。
# ============================================================
import asyncio
import os
import uvicorn
from app import create_apps


async def main():
    decoy, management = create_apps()
    servers = [uvicorn.Server(uvicorn.Config(app, host='0.0.0.0', port=int(port),
                                            proxy_headers=False, server_header=False))
               for app, port in [(decoy, os.getenv('SUISHI_PORT', '8910')),
                                 (management, os.getenv('SUISHI_ADMIN_PORT', '8911'))]]
    await asyncio.gather(*(server.serve() for server in servers))


if __name__ == '__main__':
    asyncio.run(main())
