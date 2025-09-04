import React from 'react';
import { Card, Row, Col, Typography, Button, Space, Statistic, Badge } from 'antd';
import {
  FileTextOutlined,
  FolderOpenOutlined,
  UnorderedListOutlined,
  BarChartOutlined,
  CloudSyncOutlined,
  SafetyOutlined,
  ThunderboltOutlined,
  GlobalOutlined,
  RocketOutlined
} from '@ant-design/icons';

const { Title, Paragraph, Text } = Typography;

const HomePage = ({ onNavigate }) => {
  // 功能卡片数据
  const features = [
    {
      key: 'single',
      title: '单个分析',
      description: '选择单个日志文件进行深度分析，快速定位问题根源',
      icon: <FileTextOutlined />,
      color: '#667eea',
      stats: { label: '支持格式', value: '10+' }
    },
    {
      key: 'bulk',
      title: '批量分析',
      description: '上传压缩包，自动解压并分析所有日志文件',
      icon: <FolderOpenOutlined />,
      color: '#52c41a',
      stats: { label: '并发处理', value: '多文件' }
    },
    {
      key: 'rules',
      title: '规则管理',
      description: '管理本地和服务端规则，支持双向智能同步',
      icon: <UnorderedListOutlined />,
      color: '#722ed1',
      stats: { label: '规则数量', value: '100+' }
    },
    {
      key: 'report',
      title: '分析报告',
      description: '查看详细的分析结果和生成专业分析报告',
      icon: <BarChartOutlined />,
      color: '#fa8c16',
      stats: { label: '报告格式', value: 'HTML/PDF' }
    }
  ];

  // 特性亮点
  const highlights = [
    {
      icon: <CloudSyncOutlined />,
      title: '双向同步',
      description: '本地和服务端规则智能同步',
      color: '#1890ff'
    },
    {
      icon: <SafetyOutlined />,
      title: '安全可靠',
      description: '本地处理，数据安全有保障',
      color: '#52c41a'
    },
    {
      icon: <ThunderboltOutlined />,
      title: '高效处理',
      description: '多线程并发，快速分析大文件',
      color: '#faad14'
    },
    {
      icon: <GlobalOutlined />,
      title: '跨平台',
      description: '支持Windows和macOS系统',
      color: '#722ed1'
    }
  ];

  const handleFeatureClick = (tabKey) => {
    if (onNavigate) {
      onNavigate(tabKey);
    }
  };

  return (
    <div className="page-container fade-in">
      {/* 欢迎区域 */}
      <div className="page-header">
        <Row align="middle" gutter={[24, 16]}>
          <Col flex="auto">
            <Title className="page-title">
              欢迎使用日志分析工具
            </Title>
            <Paragraph className="page-subtitle">
              专业的桌面端日志分析工具，支持单个文件和批量压缩包分析，提供强大的规则管理和双向同步功能
            </Paragraph>
          </Col>
          <Col>
            <Space size="large">
              <Button 
                type="primary" 
                size="large"
                icon={<RocketOutlined />}
                className="modern-button"
                onClick={() => handleFeatureClick('single')}
                style={{
                  background: 'linear-gradient(135deg, #667eea, #764ba2)',
                  border: 'none',
                  borderRadius: '12px',
                  height: '48px',
                  padding: '0 24px',
                  fontWeight: '600'
                }}
              >
                立即开始
              </Button>
              <Button 
                size="large"
                onClick={() => handleFeatureClick('rules')}
                style={{
                  borderRadius: '12px',
                  height: '48px',
                  padding: '0 24px',
                  fontWeight: '500'
                }}
              >
                管理规则
              </Button>
            </Space>
          </Col>
        </Row>
      </div>

      {/* 主要功能 */}
      <div className="page-content">
        <Title level={3} style={{ 
          marginBottom: '32px',
          display: 'flex',
          alignItems: 'center',
          gap: '12px',
          color: '#262626'
        }}>
          🚀 主要功能
        </Title>
        
        <div className="feature-grid">
          {features.map((feature) => (
            <div
              key={feature.key}
              className="feature-card"
              onClick={() => handleFeatureClick(feature.key)}
            >
              <div className="feature-card-content">
                <div className="feature-icon" style={{ color: feature.color }}>
                  {feature.icon}
                </div>
                <div className="feature-title">
                  {feature.title}
                </div>
                <div className="feature-description">
                  {feature.description}
                </div>
                <div style={{ 
                  marginTop: '20px',
                  paddingTop: '20px',
                  borderTop: '1px solid #f0f0f0'
                }}>
                  <Statistic
                    title={feature.stats.label}
                    value={feature.stats.value}
                    valueStyle={{ 
                      color: feature.color, 
                      fontSize: '16px',
                      fontWeight: '600'
                    }}
                  />
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* 特性亮点 */}
        <Title level={3} style={{ 
          marginTop: '64px',
          marginBottom: '32px',
          display: 'flex',
          alignItems: 'center',
          gap: '12px',
          color: '#262626'
        }}>
          ✨ 特性亮点
        </Title>
        
        <Row gutter={[24, 24]} style={{ marginBottom: '48px' }}>
          {highlights.map((highlight, index) => (
            <Col xs={24} sm={12} lg={6} key={index}>
              <Card 
                style={{ 
                  height: '100%',
                  textAlign: 'center',
                  borderRadius: '16px',
                  border: '1px solid rgba(0, 0, 0, 0.06)',
                  boxShadow: '0 4px 20px rgba(0, 0, 0, 0.08)'
                }}
                bodyStyle={{ padding: '32px 24px' }}
              >
                <div style={{ 
                  marginBottom: '20px',
                  fontSize: '32px',
                  color: highlight.color
                }}>
                  {highlight.icon}
                </div>
                <Title level={5} style={{ 
                  marginBottom: '12px',
                  color: '#262626',
                  fontWeight: '600'
                }}>
                  {highlight.title}
                </Title>
                <Text style={{ 
                  color: '#8c8c8c',
                  fontSize: '14px',
                  lineHeight: '1.6'
                }}>
                  {highlight.description}
                </Text>
              </Card>
            </Col>
          ))}
        </Row>

        {/* 快速开始 */}
        <Card 
          title={
            <span style={{
              fontSize: '18px',
              fontWeight: '600',
              color: '#262626',
              display: 'flex',
              alignItems: 'center',
              gap: '8px'
            }}>
              🎯 快速开始
            </span>
          }
          style={{ 
            marginTop: '48px',
            borderRadius: '16px',
            border: '1px solid rgba(0, 0, 0, 0.06)',
            boxShadow: '0 4px 20px rgba(0, 0, 0, 0.08)'
          }}
          bodyStyle={{ padding: '32px' }}
        >
          <Row gutter={[24, 24]}>
            <Col xs={24} md={8}>
              <div style={{ textAlign: 'center', padding: '16px' }}>
                <div style={{ 
                  width: '56px', 
                  height: '56px', 
                  borderRadius: '50%', 
                  background: 'linear-gradient(135deg, #667eea, #764ba2)', 
                  color: 'white', 
                  display: 'flex', 
                  alignItems: 'center', 
                  justifyContent: 'center', 
                  margin: '0 auto 16px',
                  fontSize: '24px',
                  fontWeight: '700',
                  boxShadow: '0 8px 24px rgba(102, 126, 234, 0.3)'
                }}>
                  1
                </div>
                <Title level={5} style={{ marginBottom: '8px', color: '#262626' }}>
                  选择分析方式
                </Title>
                <Text style={{ color: '#8c8c8c', fontSize: '14px' }}>
                  选择单个文件分析或批量压缩包分析
                </Text>
              </div>
            </Col>
            
            <Col xs={24} md={8}>
              <div style={{ textAlign: 'center', padding: '16px' }}>
                <div style={{ 
                  width: '56px', 
                  height: '56px', 
                  borderRadius: '50%', 
                  background: 'linear-gradient(135deg, #52c41a, #389e0d)', 
                  color: 'white', 
                  display: 'flex', 
                  alignItems: 'center', 
                  justifyContent: 'center', 
                  margin: '0 auto 16px',
                  fontSize: '24px',
                  fontWeight: '700',
                  boxShadow: '0 8px 24px rgba(82, 196, 26, 0.3)'
                }}>
                  2
                </div>
                <Title level={5} style={{ marginBottom: '8px', color: '#262626' }}>
                  上传日志文件
                </Title>
                <Text style={{ color: '#8c8c8c', fontSize: '14px' }}>
                  拖拽或点击上传需要分析的日志文件
                </Text>
              </div>
            </Col>
            
            <Col xs={24} md={8}>
              <div style={{ textAlign: 'center', padding: '16px' }}>
                <div style={{ 
                  width: '56px', 
                  height: '56px', 
                  borderRadius: '50%', 
                  background: 'linear-gradient(135deg, #722ed1, #531dab)', 
                  color: 'white', 
                  display: 'flex', 
                  alignItems: 'center', 
                  justifyContent: 'center', 
                  margin: '0 auto 16px',
                  fontSize: '24px',
                  fontWeight: '700',
                  boxShadow: '0 8px 24px rgba(114, 46, 209, 0.3)'
                }}>
                  3
                </div>
                <Title level={5} style={{ marginBottom: '8px', color: '#262626' }}>
                  查看分析结果
                </Title>
                <Text style={{ color: '#8c8c8c', fontSize: '14px' }}>
                  获得详细的分析报告和错误上下文
                </Text>
              </div>
            </Col>
          </Row>
        </Card>

        {/* 版本信息 */}
        <div style={{ 
          textAlign: 'center', 
          marginTop: '64px', 
          padding: '32px',
          background: 'linear-gradient(135deg, #f8f9fa, #ffffff)',
          borderRadius: '16px',
          border: '1px solid rgba(0, 0, 0, 0.06)'
        }}>
          <Text style={{ 
            color: '#8c8c8c',
            fontSize: '14px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '16px',
            flexWrap: 'wrap'
          }}>
            <span>日志分析工具 v1.0.0</span>
            <Badge status="success" text="运行正常" />
            <span>© 2024 LogAnalyzer Team</span>
          </Text>
        </div>
      </div>
    </div>
  );
};

export default HomePage; 