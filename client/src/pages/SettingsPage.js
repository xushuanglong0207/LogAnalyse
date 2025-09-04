import React from 'react';
import { Typography } from 'antd';

const { Title } = Typography;

const SettingsPage = () => {
  return (
    <div className="page-container">
      <div className="page-header">
        <Title level={2}>设置</Title>
      </div>
      <div className="page-content">
        <p>应用设置功能正在开发中...</p>
      </div>
    </div>
  );
};

export default SettingsPage; 