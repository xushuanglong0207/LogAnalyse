import React from 'react';
import { Typography } from 'antd';

const { Title } = Typography;

const RuleManagePage = () => {
  return (
    <div className="page-container">
      <div className="page-header">
        <Title level={2}>规则管理</Title>
      </div>
      <div className="page-content">
        <p>规则管理和同步功能正在开发中...</p>
      </div>
    </div>
  );
};

export default RuleManagePage; 