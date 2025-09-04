import React from 'react';
import { Typography } from 'antd';

const { Title } = Typography;

const SingleAnalysisPage = () => {
  return (
    <div className="page-container">
      <div className="page-header">
        <Title level={2}>单个分析</Title>
      </div>
      <div className="page-content">
        <p>单个日志文件分析功能正在开发中...</p>
      </div>
    </div>
  );
};

export default SingleAnalysisPage; 