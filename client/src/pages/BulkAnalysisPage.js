import React from 'react';
import { Typography } from 'antd';

const { Title } = Typography;

const BulkAnalysisPage = () => {
  return (
    <div className="page-container">
      <div className="page-header">
        <Title level={2}>批量分析</Title>
      </div>
      <div className="page-content">
        <p>批量压缩包分析功能正在开发中...</p>
      </div>
    </div>
  );
};

export default BulkAnalysisPage; 