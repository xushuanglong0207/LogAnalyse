import React from 'react';
import { Typography } from 'antd';

const { Title } = Typography;

const ReportPage = () => {
  return (
    <div className="page-container">
      <div className="page-header">
        <Title level={2}>分析报告</Title>
      </div>
      <div className="page-content">
        <p>分析报告功能正在开发中...</p>
      </div>
    </div>
  );
};

export default ReportPage; 