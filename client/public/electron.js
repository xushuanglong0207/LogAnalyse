const { app, BrowserWindow, Menu, ipcMain, dialog, shell } = require('electron');
const path = require('path');
const isDev = require('electron-is-dev');
const fs = require('fs');
const os = require('os');

// 保持对窗口对象的全局引用，如果不这样做，当JavaScript对象被垃圾回收时，窗口将自动关闭。
let mainWindow;

async function createWindow() {
  // 创建浏览器窗口
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    minWidth: 1200,
    minHeight: 800,
    webPreferences: {
      nodeIntegration: true,
      contextIsolation: false,
      enableRemoteModule: true,
      webSecurity: false
    },
    icon: path.join(__dirname, '../assets/icon.png'), // 应用图标
    titleBarStyle: process.platform === 'darwin' ? 'hiddenInset' : 'default',
    show: false // 先不显示，等加载完成后再显示
  });

  // 加载应用
  let startUrl;

  // 检查是否有 React 开发服务器运行
  const checkReactServer = async () => {
    try {
      const http = require('http');
      return new Promise((resolve) => {
        const req = http.get('http://localhost:3000', (res) => {
          resolve(true);
        });
        req.on('error', () => {
          resolve(false);
        });
        req.setTimeout(1000, () => {
          req.destroy();
          resolve(false);
        });
      });
    } catch (e) {
      return false;
    }
  };

  if (isDev) {
    // 开发环境：检查 React 服务器是否可用
    const reactServerAvailable = await checkReactServer();
    if (reactServerAvailable) {
      startUrl = 'http://localhost:3000';
    } else {
      // 优先使用完整应用页面
      const fullAppPath = path.join(__dirname, '../full-app.html');
      if (fs.existsSync(fullAppPath)) {
        startUrl = `file://${fullAppPath}`;
        console.log('React dev server not available, using full app HTML');
      } else {
        startUrl = `file://${path.join(__dirname, '../standalone.html')}`;
        console.log('Using standalone HTML');
      }
    }
  } else {
    // 生产环境：先尝试构建版本，失败则使用完整应用页面
    const buildPath = path.join(__dirname, '../build/index.html');
    if (fs.existsSync(buildPath)) {
      startUrl = `file://${buildPath}`;
    } else {
      const fullAppPath = path.join(__dirname, '../full-app.html');
      if (fs.existsSync(fullAppPath)) {
        startUrl = `file://${fullAppPath}`;
      } else {
        startUrl = `file://${path.join(__dirname, '../standalone.html')}`;
      }
    }
  }

  console.log('Loading URL:', startUrl);
  mainWindow.loadURL(startUrl);

  // 窗口加载完成后显示
  mainWindow.once('ready-to-show', () => {
    mainWindow.show();
    
    // 开发环境下自动打开DevTools
    if (isDev) {
      mainWindow.webContents.openDevTools();
    }
  });

  // 当窗口关闭时触发
  mainWindow.on('closed', () => {
    mainWindow = null;
  });

  // 处理外部链接
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url);
    return { action: 'deny' };
  });
}

// 当Electron完成初始化并准备创建浏览器窗口时调用此方法
app.whenReady().then(createWindow);

// IPC 处理程序
ipcMain.handle('select-file', async (event, options) => {
  try {
    const result = await dialog.showOpenDialog(mainWindow, {
      properties: ['openFile'],
      filters: options.filters || [
        { name: '日志文件', extensions: ['log', 'txt', 'out'] },
        { name: '压缩文件', extensions: ['zip', 'rar', '7z', 'tar', 'gz', 'tgz'] },
        { name: '所有文件', extensions: ['*'] }
      ]
    });
    return result;
  } catch (error) {
    console.error('文件选择失败:', error);
    return { canceled: true, filePaths: [] };
  }
});

// 当所有窗口都关闭时退出应用
app.on('window-all-closed', () => {
  // 在macOS上，应用程序及其菜单栏通常保持活动状态，直到用户明确退出
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('activate', () => {
  // 在macOS上，当应用程序图标被点击并且没有其他窗口打开时，通常会重新创建窗口
  if (BrowserWindow.getAllWindows().length === 0) {
    createWindow();
  }
});

// IPC通信处理已在上面定义

// 选择文件夹
ipcMain.handle('select-folder', async (event, options = {}) => {
  const result = await dialog.showOpenDialog(mainWindow, {
    properties: ['openDirectory'],
    ...options
  });
  return result;
});

// 保存文件
ipcMain.handle('save-file', async (event, options = {}) => {
  const result = await dialog.showSaveDialog(mainWindow, {
    filters: [
      { name: 'JSON文件', extensions: ['json'] },
      { name: 'HTML报告', extensions: ['html'] },
      { name: '所有文件', extensions: ['*'] }
    ],
    ...options
  });
  return result;
});

// 读取文件
ipcMain.handle('read-file', async (event, filePath) => {
  try {
    const data = fs.readFileSync(filePath, 'utf8');
    return { success: true, data };
  } catch (error) {
    return { success: false, error: error.message };
  }
});

// 写入文件
ipcMain.handle('write-file', async (event, filePath, data) => {
  try {
    fs.writeFileSync(filePath, data, 'utf8');
    return { success: true };
  } catch (error) {
    return { success: false, error: error.message };
  }
});

// 获取应用信息
ipcMain.handle('get-app-info', async () => {
  return {
    version: app.getVersion(),
    platform: process.platform,
    arch: process.arch,
    userDataPath: app.getPath('userData'),
    tempPath: os.tmpdir()
  };
});

// 获取用户数据目录
ipcMain.handle('get-user-data-path', () => {
  return app.getPath('userData');
});

// 显示消息框
ipcMain.handle('show-message-box', async (event, options) => {
  const result = await dialog.showMessageBox(mainWindow, options);
  return result;
});

// 打开外部链接
ipcMain.handle('open-external', async (event, url) => {
  shell.openExternal(url);
});

// 设置应用菜单
function setApplicationMenu() {
  const template = [
    {
      label: '视图',
      submenu: [
        { role: 'reload' },
        { role: 'forceReload' },
        { role: 'toggleDevTools' },
        { type: 'separator' },
        { role: 'resetZoom' },
        { role: 'zoomIn' },
        { role: 'zoomOut' },
        { type: 'separator' },
        { role: 'togglefullscreen' }
      ]
    }
  ];

  // macOS特殊处理
  if (process.platform === 'darwin') {
    template.unshift({
      label: app.getName(),
      submenu: [
        { role: 'about' },
        { type: 'separator' },
        { role: 'services' },
        { type: 'separator' },
        { role: 'hide' },
        { role: 'hideOthers' },
        { role: 'unhide' },
        { type: 'separator' },
        { role: 'quit' }
      ]
    });
  }

  const menu = Menu.buildFromTemplate(template);
  Menu.setApplicationMenu(menu);
}

// 应用准备就绪时设置菜单
app.whenReady().then(() => {
  setApplicationMenu();
});

// 防止应用被意外关闭
app.on('before-quit', (event) => {
  // 这里可以添加保存工作的逻辑
});

// 处理协议
app.setAsDefaultProtocolClient('log-analyzer'); 