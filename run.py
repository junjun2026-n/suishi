# 文件名称：run.py
# 生成日期：2026-11-21 | 修改日期：2026-11-21 | 版本信息：v0.261115
# 作者：JUN
# 备注：本程序由AI辅助完成。启动独立业务和管理服务；端口须分别放行。
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
