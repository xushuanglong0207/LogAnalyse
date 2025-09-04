import React from 'react';
import { Layout, Menu, Button, Typography, Divider } from 'antd';
import { useNavigate, useLocation } from 'react-router-dom';
import {
  HomeOutlined,
  FileTextOutlined,
  FolderOpenOutlined,
  SettingOutlined,
  UnorderedListOutlined,
  BarChartOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  BulbOutlined,
  BulbFilled
} from '@ant-design/icons';

const { Sider } = Layout;
const { Text } = Typography;

const Sidebar = ({ collapsed, onToggle, currentTheme, onThemeToggle }) => {
  const navigate = useNavigate();
  const location = useLocation();

  // 菜单项配置
  const menuItems = [
    {
      key: '/',
      icon: <HomeOutlined />,
      label: '首页',
      title: '应用首页'
    },
    {
      key: '/single-analysis',
      icon: <FileTextOutlined />,
      label: '单个分析',
      title: '分析单个日志文件'
    },
    {
      key: '/bulk-analysis',
      icon: <FolderOpenOutlined />,
      label: '批量分析',
      title: '分析压缩包中的多个日志文件'
    },
    {
      key: 'divider-1',
      type: 'divider'
    },
    {
      key: '/rules',
      icon: <UnorderedListOutlined />,
      label: '规则管理',
      title: '管理日志分析规则'
    },
    {
      key: '/report',
      icon: <BarChartOutlined />,
      label: '分析报告',
      title: '查看分析结果和报告'
    },
    {
      key: 'divider-2',
      type: 'divider'
    },
    {
      key: '/settings',
      icon: <SettingOutlined />,
      label: '设置',
      title: '应用设置和配置'
    }
  ];

  // 处理菜单点击
  const handleMenuClick = ({ key }) => {
    if (key.startsWith('divider-')) return;
    navigate(key);
  };

  // 获取当前选中的菜单项
  const selectedKeys = [location.pathname];

  // 过滤掉分隔符，生成实际的菜单项
  const actualMenuItems = menuItems.filter(item => !item.key.startsWith('divider-'));

  return (
    <Sider 
      trigger={null} 
      collapsible 
      collapsed={collapsed}
      width={240}
      collapsedWidth={64}
      theme="light"
      style={{
        overflow: 'auto',
        height: '100vh',
        position: 'fixed',
        left: 0,
        top: 0,
        bottom: 0,
        zIndex: 1000,
        boxShadow: '2px 0 8px rgba(0, 0, 0, 0.06)',
        background: currentTheme === 'dark' ? '#141414' : '#ffffff'
      }}
    >
      {/* 应用标题 */}
      <div style={{ 
        padding: collapsed ? '16px 8px' : '16px 24px', 
        textAlign: collapsed ? 'center' : 'left',
        borderBottom: `1px solid ${currentTheme === 'dark' ? '#303030' : '#f0f0f0'}`
      }}>
        {collapsed ? (
          <div style={{ 
            fontSize: '24px', 
            fontWeight: 'bold', 
            color: '#667eea',
            lineHeight: '32px'
          }}>
            📊
          </div>
        ) : (
          <div>
            <Text style={{ 
              fontSize: '18px', 
              fontWeight: 'bold', 
              color: '#667eea',
              display: 'block'
            }}>
              📊 日志分析工具
            </Text>
            <Text style={{ 
              fontSize: '12px', 
              color: currentTheme === 'dark' ? '#8c8c8c' : '#999',
              display: 'block',
              marginTop: '4px'
            }}>
              Desktop Log Analyzer
            </Text>
          </div>
        )}
      </div>

      {/* 折叠按钮 */}
      <div style={{ 
        padding: '12px', 
        textAlign: collapsed ? 'center' : 'right',
        borderBottom: `1px solid ${currentTheme === 'dark' ? '#303030' : '#f0f0f0'}`
      }}>
        <Button
          type="text"
          icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
          onClick={onToggle}
          size="small"
          style={{
            fontSize: '16px',
            width: collapsed ? '32px' : 'auto',
            height: '32px'
          }}
        />
        
        {!collapsed && (
          <Button
            type="text"
            icon={currentTheme === 'dark' ? <BulbFilled /> : <BulbOutlined />}
            onClick={onThemeToggle}
            size="small"
            style={{
              fontSize: '16px',
              width: '32px',
              height: '32px',
              marginLeft: '8px'
            }}
            title={currentTheme === 'dark' ? '切换到浅色主题' : '切换到深色主题'}
          />
        )}
      </div>

      {/* 主菜单 */}
      <Menu
        theme={currentTheme === 'dark' ? 'dark' : 'light'}
        mode="inline"
        selectedKeys={selectedKeys}
        onClick={handleMenuClick}
        style={{ 
          border: 'none',
          paddingTop: '8px'
        }}
        items={actualMenuItems.map(item => ({
          key: item.key,
          icon: item.icon,
          label: item.label,
          title: collapsed ? item.title : undefined
        }))}
      />

      {/* 底部信息 */}
      {!collapsed && (
        <div style={{
          position: 'absolute',
          bottom: '16px',
          left: '16px',
          right: '16px'
        }}>
          <Divider style={{ margin: '12px 0' }} />
          <div style={{ 
            textAlign: 'center',
            color: currentTheme === 'dark' ? '#8c8c8c' : '#999',
            fontSize: '12px'
          }}>
            <div>版本 1.0.0</div>
            <div style={{ marginTop: '4px' }}>
              © 2024 LogAnalyzer Team
            </div>
          </div>
        </div>
      )}

      {/* 主题切换按钮 - 折叠状态下显示在底部 */}
      {collapsed && (
        <div style={{
          position: 'absolute',
          bottom: '16px',
          left: '50%',
          transform: 'translateX(-50%)'
        }}>
          <Button
            type="text"
            icon={currentTheme === 'dark' ? <BulbFilled /> : <BulbOutlined />}
            onClick={onThemeToggle}
            size="small"
            style={{
              fontSize: '16px',
              width: '32px',
              height: '32px'
            }}
            title={currentTheme === 'dark' ? '切换到浅色主题' : '切换到深色主题'}
          />
        </div>
      )}
    </Sider>
  );
};

export default Sidebar; 