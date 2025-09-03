'use client'

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string }
  reset: () => void
}) {
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
      <h2 style={{ color: '#ef4444', marginBottom: '16px' }}>页面出错了!</h2>
      <p style={{ color: '#6b7280', marginBottom: '24px', textAlign: 'center' }}>
        很抱歉，页面遇到了一个错误。请尝试刷新页面或稍后再试。
      </p>
      <button
        onClick={reset}
        style={{
          backgroundColor: '#3b82f6',
          color: 'white',
          padding: '12px 24px',
          borderRadius: '8px',
          border: 'none',
          cursor: 'pointer',
          fontSize: '16px'
        }}
      >
        重试
      </button>
    </div>
  )
}