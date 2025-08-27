// @ts-nocheck
'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { Eye, EyeOff, LogIn, TrendingUp, BarChart3, Activity } from 'lucide-react'

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
	const [form, setForm] = useState({ username: '', password: '', remember: false })
	const [loading, setLoading] = useState(false)
	const [error, setError] = useState('')
	const [showPwd, setShowPwd] = useState(false)
	const [mounted, setMounted] = useState(false)

	useEffect(() => {
		setMounted(true)
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

	if (!mounted) return null

	return (
		<div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-100 flex flex-col relative overflow-hidden">
			{/* Animated background elements */}
			<div className="absolute inset-0 overflow-hidden">
				<div className="absolute -top-24 -right-24 w-96 h-96 bg-gradient-to-br from-blue-400/20 to-indigo-600/20 rounded-full blur-3xl animate-pulse"></div>
				<div className="absolute -bottom-24 -left-24 w-96 h-96 bg-gradient-to-tr from-violet-400/20 to-purple-600/20 rounded-full blur-3xl animate-pulse delay-1000"></div>
				<div className="absolute top-1/3 right-1/4 w-32 h-32 bg-gradient-to-br from-cyan-400/30 to-blue-500/30 rounded-full blur-2xl animate-bounce delay-2000"></div>
			</div>

			{/* Header */}
			<header className="relative z-10 pt-8 pb-4">
				<div className="flex flex-col items-center space-y-4">
					<div className="relative">
						<div className="w-16 h-16 bg-gradient-to-br from-blue-600 to-violet-600 rounded-2xl flex items-center justify-center shadow-2xl shadow-blue-500/25 animate-pulse">
							<BarChart3 className="w-8 h-8 text-white" />
						</div>
						<div className="absolute -top-1 -right-1 w-6 h-6 bg-gradient-to-br from-green-400 to-emerald-500 rounded-full flex items-center justify-center shadow-lg">
							<Activity className="w-3 h-3 text-white" />
						</div>
					</div>
					<div className="text-center">
						<h1 className="text-4xl font-black bg-gradient-to-r from-gray-900 via-blue-800 to-violet-800 bg-clip-text text-transparent">
							日志分析平台
						</h1>
						<p className="text-gray-600 text-sm mt-2 font-medium">快速分析日志错误，问题归类</p>
					</div>
				</div>
			</header>

			{/* Main content */}
			<div className="flex-1 flex items-center justify-center px-4 py-8">
				<div className="w-full max-w-md">
					{/* Login card */}
					<div className="relative">
						{/* Card background with glassmorphism */}
						<div className="absolute inset-0 bg-gradient-to-br from-white/70 to-white/30 backdrop-blur-xl rounded-3xl shadow-2xl shadow-blue-500/10 border border-white/50"></div>
						
						<div className="relative p-8 space-y-8">
							{/* Card header */}
							<div className="text-center space-y-2">
								<h2 className="text-2xl font-bold text-gray-900">欢迎回来</h2>
								<p className="text-gray-600 text-sm">请登录您的账户以继续</p>
							</div>

							{/* Login form */}
							<div className="space-y-6">
								{/* Username field */}
								<div className="space-y-2">
									<label className="block text-sm font-semibold text-gray-700">用户名</label>
									<div className="relative group">
										<input
											type="text"
											value={form.username}
											onChange={(e) => setForm({ ...form, username: e.target.value })}
											placeholder="请输入用户名"
											autoComplete="username"
											className="w-full px-4 py-3.5 bg-white/50 border border-gray-200/60 rounded-xl focus:bg-white focus:border-blue-500 focus:ring-4 focus:ring-blue-500/10 transition-all duration-200 text-gray-900 placeholder-gray-500 font-medium group-hover:border-gray-300"
										/>
									</div>
								</div>

								{/* Password field */}
								<div className="space-y-2">
									<label className="block text-sm font-semibold text-gray-700">密码</label>
									<div className="relative group">
										<input
											type={showPwd ? 'text' : 'password'}
											value={form.password}
											onChange={(e) => setForm({ ...form, password: e.target.value })}
											placeholder="请输入密码"
											autoComplete="current-password"
											onKeyDown={(e) => { if (e.key === 'Enter') doLogin() }}
											className="w-full px-4 py-3.5 pr-12 bg-white/50 border border-gray-200/60 rounded-xl focus:bg-white focus:border-blue-500 focus:ring-4 focus:ring-blue-500/10 transition-all duration-200 text-gray-900 placeholder-gray-500 font-medium group-hover:border-gray-300"
										/>
										<button
											type="button"
											onClick={() => setShowPwd(v => !v)}
											className="absolute right-3 top-1/2 -translate-y-1/2 p-1.5 text-gray-400 hover:text-gray-600 transition-colors duration-200 rounded-lg hover:bg-gray-100"
										>
											{showPwd ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
										</button>
									</div>
								</div>

								{/* Remember me */}
								<div className="flex items-center justify-between">
									<label className="flex items-center space-x-3 cursor-pointer group">
										<div className="relative">
											<input
												type="checkbox"
												checked={form.remember}
												onChange={(e) => setForm({ ...form, remember: e.target.checked })}
												className="sr-only"
											/>
											<div className={`w-5 h-5 rounded-lg border-2 transition-all duration-200 ${form.remember ? 'bg-blue-600 border-blue-600' : 'border-gray-300 group-hover:border-blue-400'}`}>
												{form.remember && (
													<svg className="w-3 h-3 text-white absolute top-0.5 left-0.5" fill="currentColor" viewBox="0 0 20 20">
														<path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
													</svg>
												)}
											</div>
										</div>
										<span className="text-sm font-medium text-gray-700 group-hover:text-blue-600 transition-colors duration-200">保持登录</span>
									</label>
								</div>

								{/* Error message */}
								{error && (
									<div className="p-3 bg-red-50 border border-red-200 rounded-xl">
										<p className="text-sm font-medium text-red-600">{error}</p>
									</div>
								)}

								{/* Login button */}
								<button
									onClick={doLogin}
									disabled={loading}
									className="w-full group relative py-4 px-6 bg-gradient-to-r from-blue-600 to-violet-600 hover:from-blue-700 hover:to-violet-700 disabled:from-gray-400 disabled:to-gray-500 text-white font-bold rounded-xl shadow-xl shadow-blue-500/25 hover:shadow-blue-500/40 disabled:shadow-none transition-all duration-300 transform hover:scale-[1.02] disabled:scale-100 disabled:cursor-not-allowed"
								>
									<div className="flex items-center justify-center space-x-2">
										{loading ? (
											<>
												<div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
												<span>登录中...</span>
											</>
										) : (
											<>
												<LogIn className="w-5 h-5 group-hover:rotate-12 transition-transform duration-200" />
												<span>登录</span>
											</>
										)}
									</div>
								</button>
							</div>
						</div>
					</div>

					{/* Feature highlights */}
					<div className="mt-8 grid grid-cols-3 gap-4">
						<div className="text-center group cursor-default">
							<div className="w-10 h-10 mx-auto bg-gradient-to-br from-violet-100 to-purple-100 rounded-xl flex items-center justify-center mb-2 group-hover:scale-110 transition-transform duration-200">
								<BarChart3 className="w-5 h-5 text-violet-600" />
							</div>
							<p className="text-xs font-medium text-gray-600">快速分析</p>
						</div>
						<div className="text-center group cursor-default">
							<div className="w-10 h-10 mx-auto bg-gradient-to-br from-emerald-100 to-teal-100 rounded-xl flex items-center justify-center mb-2 group-hover:scale-110 transition-transform duration-200">
								<Activity className="w-5 h-5 text-emerald-600" />
							</div>
							<p className="text-xs font-medium text-gray-600">问题分类</p>
						</div>
						<div className="text-center group cursor-default">
							<div className="w-10 h-10 mx-auto bg-gradient-to-br from-blue-100 to-indigo-100 rounded-xl flex items-center justify-center mb-2 group-hover:scale-110 transition-transform duration-200">
								<TrendingUp className="w-5 h-5 text-blue-600" />
							</div>
							<p className="text-xs font-medium text-gray-600">趋势监控</p>
						</div>
					</div>
				</div>
			</div>

			{/* Footer */}
			<footer className="relative z-10 pb-8 text-center">
				<p className="text-xs text-gray-500 font-medium">
					版本 V1.0.0 · 作者 Carl.Xu · © 2025 日志分析平台
				</p>
			</footer>
		</div>
	)
}