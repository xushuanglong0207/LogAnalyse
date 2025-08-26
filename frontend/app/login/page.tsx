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
		<div className="center-page" style={{ position: 'relative', paddingTop: 80, paddingBottom: 60 }}>
			<h1 style={{ position: 'absolute', top: 20, left: 0, right: 0, textAlign: 'center', fontSize: 32, fontWeight: 900, color: '#111827' }}>日志分析平台</h1>
			<div className="ui-card" style={{ width: 'min(520px, 92vw)' }}>
				<div className="modal-header"><h1 className="modal-title">登录</h1></div>
				<div className="modal-body stack-16">
					<div className="form-col">
						<div className="label">用户名</div>
						<input className="ui-input" value={form.username} onChange={(e) => setForm({ ...form, username: e.target.value })} placeholder="用户名 (默认 admin)" autoComplete="username" />
					</div>
					<div className="form-col">
						<div className="label">密码</div>
						<div style={{ position: 'relative' }}>
							<input className="ui-input" type={showPwd ? 'text' : 'password'} value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} placeholder="密码 (默认 admin123)" autoComplete="current-password" onKeyDown={(e) => { if (e.key === 'Enter') doLogin() }} style={{ paddingRight: 44 }} />
							<button className="btn btn-outline" onClick={() => setShowPwd(v => !v)} aria-label="toggle password" style={{ position: 'absolute', right: 6, top: 6, padding: '6px 10px' }}>{showPwd ? '隐藏' : '显示'}</button>
						</div>
					</div>
					<label style={{ display: 'flex', alignItems: 'center', gap: 8, userSelect: 'none' }}>
						<input type="checkbox" checked={form.remember} onChange={(e) => setForm({ ...form, remember: e.target.checked })} /> 保持登录
					</label>
					{error && <div style={{ color: '#b91c1c', fontSize: 12 }}>{error}</div>}
				</div>
				<div className="modal-footer">
					<button disabled={loading} onClick={doLogin} className="btn btn-primary" style={{ minWidth: 120 }}>{loading ? '登录中...' : '登录'}</button>
				</div>
			</div>
			<div style={{ position: 'absolute', bottom: 20, left: 0, right: 0, textAlign: 'center', color: '#6b7280', fontSize: 12 }}>版本：V1.0.0  作者：Carl.Xu</div>
		</div>
	)
} 