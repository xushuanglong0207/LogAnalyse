export default function NotFound() {
  return (
    <div style={{ 
      display: 'flex', 
      flexDirection: 'column', 
      alignItems: 'center', 
      justifyContent: 'center', 
      height: '100vh',
      padding: '20px',
      fontFamily: 'system-ui, sans-serif'
    }}>
      <h2 style={{ color: '#374151', marginBottom: '16px', fontSize: '24px' }}>404 - 页面未找到</h2>
      <p style={{ color: '#6b7280', marginBottom: '24px', textAlign: 'center' }}>
        抱歉，您访问的页面不存在。
      </p>
      <a 
        href="/"
        style={{
          backgroundColor: '#3b82f6',
          color: 'white',
          padding: '12px 24px',
          borderRadius: '8px',
          textDecoration: 'none',
          fontSize: '16px'
        }}
      >
        返回首页
      </a>
    </div>
  )
}