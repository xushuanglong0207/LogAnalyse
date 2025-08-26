FROM node:20-alpine

WORKDIR /app

# 设置npm配置
RUN npm config set legacy-peer-deps true

# 复制package文件
COPY package*.json ./

# 安装依赖
RUN npm install --legacy-peer-deps --verbose

# 复制源代码
COPY . .

# 创建.npmrc文件
RUN echo "legacy-peer-deps=true" > .npmrc

# 暴露端口
EXPOSE 3000

# 开发模式启动（跳过构建步骤以避免依赖问题）
CMD ["npm", "run", "dev"] 