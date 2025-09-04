import React, { useState, useEffect } from 'react';
import { Layout, ConfigProvider, theme, message, Tabs } from 'antd';
import { BrowserRouter as Router } from 'react-router-dom';
import zhCN from 'antd/locale/zh_CN';
import {
  HomeOutlined,
  FileTextOutlined,
  FolderOpenOutlined,
  UnorderedListOutlined,
  BarChartOutlined,
  SettingOutlined,
  BulbOutlined,
  BulbFilled
} from '@ant-design/icons';

// 导入组件
import HomePage from './pages/HomePage';
import SingleAnalysisPage from './pages/SingleAnalysisPage';
import BulkAnalysisPage from './pages/BulkAnalysisPage';
import RuleManagePage from './pages/RuleManagePage';
import SettingsPage from './pages/SettingsPage';
import ReportPage from './pages/ReportPage';

// 导入工具类
import { ElectronAPI } from './utils/electronAPI';

import './App.css';

const { Header, Content } = Layout;

function App() {
  const [currentTheme, setCurrentTheme] = useState('light');
  const [activeTab, setActiveTab] = useState('home');
  const [appInfo, setAppInfo] = useState(null);
  const [loading, setLoading] = useState(true);

  // Tab配置
  const tabItems = [
    {
      key: 'home',
      label: (
        <span>
          <HomeOutlined />
          首页
        </span>
      ),
      children: <HomePage onNavigate={setActiveTab} />,
    },
    {
      key: 'single',
      label: (
        <span>
          <FileTextOutlined />
          单个分析
        </span>
      ),
      children: <SingleAnalysisPage />,
    },
    {
      key: 'bulk',
      label: (
        <span>
          <FolderOpenOutlined />
          批量分析
        </span>
      ),
      children: <BulkAnalysisPage />,
    },
    {
      key: 'rules',
      label: (
        <span>
          <UnorderedListOutlined />
          规则管理
        </span>
      ),
      children: <RuleManagePage />,
    },
    {
      key: 'report',
      label: (
        <span>
          <BarChartOutlined />
          分析报告
        </span>
      ),
      children: <ReportPage />,
    },
    {
      key: 'settings',
      label: (
        <span>
          <SettingOutlined />
          设置
        </span>
      ),
      children: <SettingsPage onThemeChange={setCurrentTheme} currentTheme={currentTheme} />,
    },
  ];

  // 初始化应用
  useEffect(() => {
    const initApp = async () => {
      try {
        // 模拟获取应用信息（如果ElectronAPI不可用）
        try {
          const info = await ElectronAPI.getAppInfo();
          setAppInfo(info);
        } catch {
          setAppInfo({ version: '1.0.0', name: '日志分析工具' });
        }

        // 尝试加载用户设置
        try {
          const settings = await ElectronAPI.loadSettings();
          if (settings.theme) {
            setCurrentTheme(settings.theme);
          }
        } catch {
          // 使用默认设置
          console.log('使用默认设置');
        }

      } catch (error) {
        console.error('应用初始化失败:', error);
        message.error('应用初始化失败，使用默认配置');
      } finally {
        setLoading(false);
      }
    };

    initApp();
  }, []);

  // 切换主题
  const toggleTheme = () => {
    const newTheme = currentTheme === 'light' ? 'dark' : 'light';
    setCurrentTheme(newTheme);
    try {
      ElectronAPI.saveSettings({ theme: newTheme });
    } catch {
      // 如果Electron API不可用，只更新本地状态
      localStorage.setItem('theme', newTheme);
    }
  };

  // Tab切换处理
  const handleTabChange = (key) => {
    setActiveTab(key);
  };

  if (loading) {
    return (
      <div className="loading-container">
        <div className="loading-spinner"></div>
        <div className="loading-text">正在加载日志分析工具...</div>
      </div>
    );
  }

  return (
    <ConfigProvider 
      locale={zhCN}
      theme={{
        algorithm: currentTheme === 'dark' ? theme.darkAlgorithm : theme.defaultAlgorithm,
        token: {
          colorPrimary: '#667eea',
          colorInfo: '#667eea',
          borderRadius: 8,
        },
        components: {
          Tabs: {
            cardBg: currentTheme === 'dark' ? '#1f1f1f' : '#ffffff',
            cardHeight: 48,
            titleFontSize: 14,
            titleFontSizeLG: 16,
          }
        }
      }}
    >
      <Router>
        <Layout className="modern-app-layout">
          {/* 顶部标题栏 */}
          <Header className="modern-header">
            <div className="header-content">
              <div className="app-logo">
                <span className="logo-icon">📊</span>
                <span className="logo-text">日志分析工具</span>
                <span className="logo-version">v{appInfo?.version || '1.0.0'}</span>
              </div>
              
              <div className="header-actions">
                <div className="theme-toggle" onClick={toggleTheme}>
                  {currentTheme === 'dark' ? <BulbFilled /> : <BulbOutlined />}
                  <span>{currentTheme === 'dark' ? '浅色模式' : '深色模式'}</span>
                </div>
              </div>
            </div>
          </Header>

          {/* 主内容区 */}
          <Content className="modern-content">
            <div className="tab-container">
              <Tabs
                activeKey={activeTab}
                onChange={handleTabChange}
                type="card"
                size="large"
                className="main-tabs"
                items={tabItems}
                animated={{ inkBar: true, tabPane: true }}
              />
            </div>
          </Content>
        </Layout>
      </Router>
    </ConfigProvider>
  );
}

export default App; 