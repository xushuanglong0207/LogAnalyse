// @ts-nocheck
'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'

function computeApiBase(): string {
	if (typeof window !== 'undefined') {
		const protocol = window.location.protocol
		const host = window.location.hostname
		return `${protocol}//${host}:8001`
	}
	return ''
}

export default function LoginPage() {
	const router = useRouter()
	const [apiBase] = useState(computeApiBase())
	const [form, setForm] = useState({ username: 'admin', password: 'admin123', remember: true })
	const [loading, setLoading] = useState(false)
	const [error, setError] = useState('')
	const [showPwd, setShowPwd] = useState(false)

	useEffect(() => {
		if (typeof window !== 'undefined') {
			const token = localStorage.getItem('token') || sessionStorage.getItem('token')
			if (token) router.replace('/')
		}
	}, [router])

	const storeToken = (token: string, remember: boolean) => {
		if (remember) localStorage.setItem('token', token)
		else sessionStorage.setItem('token', token)
	}

	const doLogin = async () => {
		if (!form.username || !form.password) { setError('请输入用户名与密码'); return }
		setLoading(true)
		setError('')
		try {
			const r = await fetch(`${apiBase}/api/auth/login`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(form) })
			if (!r.ok) { const t = await r.text(); setError(t || '登录失败'); setLoading(false); return }
			const d = await r.json()
			storeToken(d.token, form.remember)
			router.replace('/')
		} catch (e) {
			setError('网络异常，请稍后重试')
		} finally {
			setLoading(false)
		}
	}

	return (
		<div style={{ minHeight: '100vh', display: 'grid', placeItems: 'center', background: 'radial-gradient(1400px 700px at -10% -10%, #c7d2fe 0%, transparent 60%), radial-gradient(1400px 700px at 120% -10%, #bbf7d0 0%, transparent 60%), linear-gradient(180deg, #f8fafc 0%, #eef2ff 100%)' }}>
			<div style={{ width: 'min(420px, 92vw)', background: 'rgba(255,255,255,0.9)', border: '1px solid rgba(255,255,255,0.6)', boxShadow: '0 30px 80px rgba(2,6,23,0.15)', borderRadius: 16, padding: 24 }}>
				<h1 style={{ margin: 0, fontSize: 18, fontWeight: 800, color: '#111827' }}>登录</h1>
				<div style={{ height: 12 }} />
				<div>
					<div style={{ fontSize: 12, color: '#6b7280' }}>用户名</div>
					<input value={form.username} onChange={(e) => setForm({ ...form, username: e.target.value })} placeholder="用户名 (默认 admin)" autoComplete="username" style={{ width: '100%', border: '1px solid #e5e7eb', borderRadius: 10, padding: '10px 12px' }} />
				</div>
				<div style={{ height: 10 }} />
				<div>
					<div style={{ fontSize: 12, color: '#6b7280' }}>密码</div>
					<div style={{ position: 'relative' }}>
						<input type={showPwd ? 'text' : 'password'} value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} placeholder="密码 (默认 admin123)" autoComplete="current-password" onKeyDown={(e) => { if (e.key === 'Enter') doLogin() }} style={{ width: '100%', border: '1px solid #e5e7eb', borderRadius: 10, padding: '10px 12px', paddingRight: 44 }} />
						<button onClick={() => setShowPwd(v => !v)} aria-label="toggle password" style={{ position: 'absolute', right: 6, top: 6, borderRadius: 8, padding: '6px 10px', border: '1px solid #e5e7eb', background: '#fff', cursor: 'pointer' }}>{showPwd ? '隐藏' : '显示'}</button>
					</div>
				</div>
				<div style={{ height: 8 }} />
				<label style={{ display: 'flex', alignItems: 'center', gap: 8, userSelect: 'none' }}>
					<input type="checkbox" checked={form.remember} onChange={(e) => setForm({ ...form, remember: e.target.checked })} /> 保持登录
				</label>
				<div style={{ height: 8 }} />
				{error && <div style={{ color: '#b91c1c', fontSize: 12, marginBottom: 8 }}>{error}</div>}
				<button disabled={loading} onClick={doLogin} style={{ width: '100%', background: '#2563eb', color: '#fff', padding: '10px 14px', borderRadius: 10, border: 'none', cursor: 'pointer', fontWeight: 700 }}>{loading ? '登录中...' : '登录'}</button>
				<div style={{ color: '#9ca3af', fontSize: 12, marginTop: 8 }}>默认管理员：admin / admin123</div>
			</div>
		</div>
	)
} 