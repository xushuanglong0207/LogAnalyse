/**
 * Electron API 工具类
 * 封装与主进程的通信
 */

const { ipcRenderer } = window.require ? window.require('electron') : {};

class ElectronAPI {
  /**
   * 检查是否在Electron环境中
   */
  static isElectron() {
    return !!window.require;
  }

  /**
   * 获取应用信息
   */
  static async getAppInfo() {
    if (!this.isElectron()) return null;
    try {
      return await ipcRenderer.invoke('get-app-info');
    } catch (error) {
      console.error('获取应用信息失败:', error);
      return null;
    }
  }

  /**
   * 获取用户数据目录路径
   */
  static async getUserDataPath() {
    if (!this.isElectron()) return null;
    try {
      return await ipcRenderer.invoke('get-user-data-path');
    } catch (error) {
      console.error('获取用户数据目录失败:', error);
      return null;
    }
  }

  /**
   * 选择文件
   */
  static async selectFile(options = {}) {
    if (!this.isElectron()) {
      // Web环境下的文件选择fallback
      return new Promise((resolve) => {
        const input = document.createElement('input');
        input.type = 'file';
        input.accept = options.accept || '*';
        input.onchange = (e) => {
          const files = Array.from(e.target.files);
          resolve({
            canceled: false,
            filePaths: files.map(f => f.path || f.name),
            files: files
          });
        };
        input.click();
      });
    }

    try {
      return await ipcRenderer.invoke('select-file', options);
    } catch (error) {
      console.error('选择文件失败:', error);
      return { canceled: true };
    }
  }

  /**
   * 选择文件夹
   */
  static async selectFolder(options = {}) {
    if (!this.isElectron()) return { canceled: true };
    try {
      return await ipcRenderer.invoke('select-folder', options);
    } catch (error) {
      console.error('选择文件夹失败:', error);
      return { canceled: true };
    }
  }

  /**
   * 保存文件
   */
  static async saveFile(options = {}) {
    if (!this.isElectron()) return { canceled: true };
    try {
      return await ipcRenderer.invoke('save-file', options);
    } catch (error) {
      console.error('保存文件失败:', error);
      return { canceled: true };
    }
  }

  /**
   * 读取文件
   */
  static async readFile(filePath) {
    if (!this.isElectron()) return { success: false, error: '不支持的环境' };
    try {
      return await ipcRenderer.invoke('read-file', filePath);
    } catch (error) {
      console.error('读取文件失败:', error);
      return { success: false, error: error.message };
    }
  }

  /**
   * 写入文件
   */
  static async writeFile(filePath, data) {
    if (!this.isElectron()) return { success: false, error: '不支持的环境' };
    try {
      return await ipcRenderer.invoke('write-file', filePath, data);
    } catch (error) {
      console.error('写入文件失败:', error);
      return { success: false, error: error.message };
    }
  }

  /**
   * 显示消息框
   */
  static async showMessageBox(options) {
    if (!this.isElectron()) {
      // Web环境下的消息框fallback
      const message = options.message || '';
      const detail = options.detail || '';
      const fullMessage = detail ? `${message}\n\n${detail}` : message;
      
      if (options.type === 'question') {
        return { response: confirm(fullMessage) ? 0 : 1 };
      } else {
        alert(fullMessage);
        return { response: 0 };
      }
    }

    try {
      return await ipcRenderer.invoke('show-message-box', options);
    } catch (error) {
      console.error('显示消息框失败:', error);
      return { response: 0 };
    }
  }

  /**
   * 打开外部链接
   */
  static async openExternal(url) {
    if (!this.isElectron()) {
      window.open(url, '_blank');
      return;
    }

    try {
      await ipcRenderer.invoke('open-external', url);
    } catch (error) {
      console.error('打开外部链接失败:', error);
    }
  }

  /**
   * 监听菜单事件
   */
  static onMenuEvent(event, callback) {
    if (!this.isElectron()) return;
    try {
      ipcRenderer.on(event, callback);
    } catch (error) {
      console.error('监听菜单事件失败:', error);
    }
  }

  /**
   * 移除事件监听
   */
  static removeMenuEventListener(event, callback) {
    if (!this.isElectron()) return;
    try {
      ipcRenderer.removeListener(event, callback);
    } catch (error) {
      console.error('移除事件监听失败:', error);
    }
  }

  /**
   * 移除所有事件监听
   */
  static removeAllListeners() {
    if (!this.isElectron()) return;
    try {
      ipcRenderer.removeAllListeners();
    } catch (error) {
      console.error('移除所有事件监听失败:', error);
    }
  }

  /**
   * 加载用户设置
   */
  static async loadSettings() {
    const userDataPath = await this.getUserDataPath();
    if (!userDataPath) return {};

    const settingsPath = `${userDataPath}/settings.json`;
    const result = await this.readFile(settingsPath);
    
    if (result.success) {
      try {
        return JSON.parse(result.data);
      } catch (error) {
        console.error('解析设置文件失败:', error);
        return {};
      }
    }
    
    return {};
  }

  /**
   * 保存用户设置
   */
  static async saveSettings(settings) {
    const userDataPath = await this.getUserDataPath();
    if (!userDataPath) return false;

    const settingsPath = `${userDataPath}/settings.json`;
    
    // 合并现有设置
    const currentSettings = await this.loadSettings();
    const newSettings = { ...currentSettings, ...settings };
    
    const result = await this.writeFile(settingsPath, JSON.stringify(newSettings, null, 2));
    return result.success;
  }

  /**
   * 加载本地规则
   */
  static async loadLocalRules() {
    const userDataPath = await this.getUserDataPath();
    if (!userDataPath) return [];

    const rulesPath = `${userDataPath}/rules.json`;
    const result = await this.readFile(rulesPath);
    
    if (result.success) {
      try {
        return JSON.parse(result.data);
      } catch (error) {
        console.error('解析规则文件失败:', error);
        return [];
      }
    }
    
    return [];
  }

  /**
   * 保存本地规则
   */
  static async saveLocalRules(rules) {
    const userDataPath = await this.getUserDataPath();
    if (!userDataPath) return false;

    const rulesPath = `${userDataPath}/rules.json`;
    const result = await this.writeFile(rulesPath, JSON.stringify(rules, null, 2));
    return result.success;
  }

  /**
   * 获取临时目录路径
   */
  static async getTempPath() {
    const appInfo = await this.getAppInfo();
    return appInfo?.tempPath || '/tmp';
  }

  /**
   * 检查文件是否存在
   */
  static async fileExists(filePath) {
    const result = await this.readFile(filePath);
    return result.success;
  }

  /**
   * 创建目录
   */
  static async createDirectory(dirPath) {
    // 这里需要在主进程中实现对应的处理
    if (!this.isElectron()) return false;
    try {
      return await ipcRenderer.invoke('create-directory', dirPath);
    } catch (error) {
      console.error('创建目录失败:', error);
      return false;
    }
  }

  /**
   * 列出目录内容
   */
  static async listDirectory(dirPath) {
    if (!this.isElectron()) return [];
    try {
      return await ipcRenderer.invoke('list-directory', dirPath);
    } catch (error) {
      console.error('列出目录内容失败:', error);
      return [];
    }
  }

  /**
   * 解压文件
   */
  static async extractArchive(archivePath, extractPath) {
    if (!this.isElectron()) return { success: false, error: '不支持的环境' };
    try {
      return await ipcRenderer.invoke('extract-archive', archivePath, extractPath);
    } catch (error) {
      console.error('解压文件失败:', error);
      return { success: false, error: error.message };
    }
  }

  /**
   * 获取文件信息
   */
  static async getFileInfo(filePath) {
    if (!this.isElectron()) return null;
    try {
      return await ipcRenderer.invoke('get-file-info', filePath);
    } catch (error) {
      console.error('获取文件信息失败:', error);
      return null;
    }
  }
}

export { ElectronAPI }; 