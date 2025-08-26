/** @type {import('next').NextConfig} */

// 自动检测API地址的函数
function getApiUrl() {
  // 如果有环境变量设置，优先使用
  if (process.env.NEXT_PUBLIC_API_URL) {
    return process.env.NEXT_PUBLIC_API_URL;
  }
  
  // 在构建时尝试获取本机IP
  const os = require('os');
  const networkInterfaces = os.networkInterfaces();
  
  // 查找第一个非本地环回的IPv4地址
  for (const name of Object.keys(networkInterfaces)) {
    for (const net of networkInterfaces[name]) {
      // 跳过非IPv4和内部地址
      if (net.family === 'IPv4' && !net.internal) {
        return `http://${net.address}:8001`;
      }
    }
  }
  
  // 回退到localhost
  return 'http://localhost:8001';
}

const nextConfig = {
  images: {
    domains: ['localhost'],
  },
  env: {
    NEXT_PUBLIC_API_URL: getApiUrl(),
  },
  // 允许从任何IP访问
  async headers() {
    return [
      {
        source: '/(.*)',
        headers: [
          {
            key: 'Access-Control-Allow-Origin',
            value: '*',
          },
        ],
      },
    ];
  },
}

module.exports = nextConfig 