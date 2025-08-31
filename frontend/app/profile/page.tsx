// @ts-nocheck
'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { 
	User, 
	Shield, 
	Eye, 
	EyeOff, 
	Save, 
	LogOut, 
	ArrowLeft,
	Camera,
	Edit3,
	Check,
	X
} from 'lucide-react'

function computeApiBase(): string {
	if (typeof window !== 'undefined') {
		const protocol = window.location.protocol
		const host = window.location.hostname
		return `${protocol}//${host}:8001`
	}
	return ''
}

export default function ProfilePage() {
	const router = useRouter()
	const [apiBase] = useState(computeApiBase())
	const [currentUser, setCurrentUser] = useState<any>(null)
	const [loading, setLoading] = useState(true)
	const [saving, setSaving] = useState(false)
	const [error, setError] = useState('')
	const [success, setSuccess] = useState('')
	
	// 表单状态
	const [profileForm, setProfileForm] = useState({
		username: '',
		email: '',
		position: ''
	})
	
	const [passwordForm, setPasswordForm] = useState({
		old_password: '',
		new_password: '',
		confirm_password: ''
	})
	
	const [showPasswords, setShowPasswords] = useState({
		old: false,
		new: false,
		confirm: false
	})

	const [activeTab, setActiveTab] = useState('profile')

	const getStoredToken = () => (typeof window === 'undefined' ? '' : (localStorage.getItem('token') || sessionStorage.getItem('token') || ''))
	
	const authedFetch = async (url: string, options: any = {}) => {
		const token = getStoredToken()
		const headers = { ...(options.headers || {}), Authorization: token ? `Bearer ${token}` : undefined }
		const resp = await fetch(url, { ...options, headers })
		if (resp.status === 401 && typeof window !== 'undefined') {
			try { localStorage.removeItem('token'); sessionStorage.removeItem('token') } catch {}
			window.location.href = '/login'
		}
		return resp
	}

	const fetchCurrentUser = async () => {
		try {
			const r = await authedFetch(`${apiBase}/api/auth/me`)
			if (r.ok) {
				const data = await r.json()
				setCurrentUser(data.user)
				setProfileForm({
					username: data.user.username || '',
					email: data.user.email || '',
					position: data.user.position || ''
				})
			}
		} catch (err) {
			setError('获取用户信息失败')
		}
	}

	useEffect(() => {
		if (!getStoredToken()) {
			router.replace('/login')
			return
		}
		// 立即设置loading为false，显示骨架屏
		setLoading(false)
		fetchCurrentUser()
	}, [])

	const updateProfile = async () => {
		setSaving(true)
		setError('')
		setSuccess('')
		
		try {
			const r = await authedFetch(`${apiBase}/api/users/${currentUser?.id}`, {
				method: 'PUT',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					email: profileForm.email,
					position: profileForm.position
				})
			})
			
			if (r.ok) {
				setSuccess('个人资料更新成功')
				// 更新本地状态
				setCurrentUser({
					...currentUser,
					email: profileForm.email,
					position: profileForm.position,
					bio: profileForm.bio
				})
			} else {
				const errorData = await r.text()
				setError(errorData || '更新失败，请稍后重试')
			}
		} catch (err) {
			setError('更新失败，请稍后重试')
		} finally {
			setSaving(false)
		}
	}

	const updatePassword = async () => {
		if (passwordForm.new_password !== passwordForm.confirm_password) {
			setError('新密码和确认密码不匹配')
			return
		}
		
		if (passwordForm.new_password.length < 6) {
			setError('新密码至少6位')
			return
		}

		setSaving(true)
		setError('')
		setSuccess('')
		
		try {
			const r = await authedFetch(`${apiBase}/api/auth/change_password`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					old_password: passwordForm.old_password,
					new_password: passwordForm.new_password
				})
			})
			
			if (r.ok) {
				setSuccess('密码修改成功，请重新登录')
				setTimeout(() => {
					localStorage.removeItem('token')
					sessionStorage.removeItem('token')
					window.location.href = '/login'
				}, 2000)
			} else {
				setError('密码修改失败，请检查原密码')
			}
		} catch (err) {
			setError('密码修改失败，请稍后重试')
		} finally {
			setSaving(false)
		}
	}

	const logout = () => {
		localStorage.removeItem('token')
		sessionStorage.removeItem('token')
		window.location.href = '/login'
	}

	const SkeletonLoader = () => (
		<div className="animate-pulse">
			<div className="h-6 bg-gray-200 rounded w-1/4 mb-4"></div>
			<div className="space-y-4">
				<div className="grid md:grid-cols-2 gap-6">
					<div className="space-y-2">
						<div className="h-4 bg-gray-200 rounded w-1/4"></div>
						<div className="h-12 bg-gray-200 rounded"></div>
					</div>
					<div className="space-y-2">
						<div className="h-4 bg-gray-200 rounded w-1/4"></div>
						<div className="h-12 bg-gray-200 rounded"></div>
					</div>
				</div>
				<div className="grid md:grid-cols-2 gap-6">
					<div className="space-y-2">
						<div className="h-4 bg-gray-200 rounded w-1/4"></div>
						<div className="h-12 bg-gray-200 rounded"></div>
					</div>
					<div className="space-y-2 md:col-span-2">
						<div className="h-4 bg-gray-200 rounded w-1/4"></div>
						<div className="h-24 bg-gray-200 rounded"></div>
					</div>
				</div>
			</div>
		</div>
	)

	if (loading) {
		return (
			<div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-100 flex items-center justify-center">
				<div className="text-center">
					<div className="w-16 h-16 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
					<p className="text-gray-600">加载中...</p>
				</div>
			</div>
		)
	}

	return (
		<div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-100">
			{/* Header */}
			<header className="bg-white/80 backdrop-blur-sm border-b border-white/20 sticky top-0 z-10">
				<div className="max-w-6xl mx-auto px-4 py-4">
					<div className="flex items-center justify-between">
						<div className="flex items-center space-x-4">
							<button
								onClick={() => router.back()}
								className="flex items-center space-x-2 px-4 py-2 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-colors duration-200"
							>
								<ArrowLeft className="w-5 h-5" />
								<span>返回</span>
							</button>
							<div className="h-6 w-px bg-gray-300" />
							<h1 className="text-2xl font-bold text-gray-900">个人中心</h1>
						</div>
						<button
							onClick={logout}
							className="flex items-center space-x-2 px-4 py-2 text-red-600 hover:text-red-700 hover:bg-red-50 rounded-lg transition-colors duration-200"
						>
							<LogOut className="w-5 h-5" />
							<span>退出登录</span>
						</button>
					</div>
				</div>
			</header>

			<div className="max-w-6xl mx-auto px-4 py-8">
				<div className="grid lg:grid-cols-4 gap-8">
					{/* Sidebar */}
					<div className="lg:col-span-1">
						<div className="bg-white/70 backdrop-blur-xl rounded-2xl shadow-xl border border-white/50 overflow-hidden sticky top-24">
							{/* User Avatar */}
							<div className="p-6 text-center border-b border-gray-100">
								<div className="relative inline-block">
									<div className="w-24 h-24 bg-gradient-to-br from-blue-600 to-violet-600 rounded-2xl flex items-center justify-center shadow-xl">
										<User className="w-12 h-12 text-white" />
									</div>
									<button className="absolute -bottom-1 -right-1 w-8 h-8 bg-white rounded-full shadow-md flex items-center justify-center hover:bg-gray-50 transition-colors duration-200">
										<Camera className="w-4 h-4 text-gray-600" />
									</button>
								</div>
								<h2 className="mt-4 text-xl font-bold text-gray-900">{currentUser?.username}</h2>
								<p className="text-gray-600 text-sm">{currentUser?.position || '未设置职位'}</p>
							</div>

							{/* Navigation */}
							<nav className="p-4">
								{[
									{ id: 'profile', label: '基本信息', icon: User },
									{ id: 'security', label: '安全设置', icon: Shield }
								].map((item) => (
									<button
										key={item.id}
										onClick={() => setActiveTab(item.id)}
										className={`w-full flex items-center space-x-3 px-4 py-3 rounded-xl transition-all duration-200 ${
											activeTab === item.id
												? 'bg-blue-50 text-blue-600 shadow-sm'
												: 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
										}`}
									>
										<item.icon className="w-5 h-5" />
										<span className="font-medium">{item.label}</span>
									</button>
								))}
							</nav>
						</div>
					</div>

					{/* Main Content */}
					<div className="lg:col-span-3">
						<div className="bg-white/70 backdrop-blur-xl rounded-2xl shadow-xl border border-white/50 overflow-hidden">
							{/* Messages */}
							{error && (
								<div className="mx-6 mt-6 p-4 bg-red-50 border border-red-200 rounded-xl">
									<div className="flex items-center">
										<X className="w-5 h-5 text-red-600 mr-2" />
										<p className="text-red-600 font-medium">{error}</p>
									</div>
								</div>
							)}
							
							{success && (
								<div className="mx-6 mt-6 p-4 bg-green-50 border border-green-200 rounded-xl">
									<div className="flex items-center">
										<Check className="w-5 h-5 text-green-600 mr-2" />
										<p className="text-green-600 font-medium">{success}</p>
									</div>
								</div>
							)}

							{/* Profile Tab */}
							{activeTab === 'profile' && (
								<div className="p-8">
									<div className="flex items-center justify-between mb-8">
										<div>
											<h3 className="text-2xl font-bold text-gray-900">基本信息</h3>
											<p className="text-gray-600 mt-1">管理您的个人资料和基本信息</p>
										</div>
										<Edit3 className="w-6 h-6 text-gray-400" />
									</div>

									{!currentUser ? (
										<SkeletonLoader />
									) : (
										<>
											<div className="grid md:grid-cols-2 gap-6">
												<div className="space-y-2">
													<label className="block text-sm font-semibold text-gray-700">用户名</label>
													<div className="relative">
														<input
															type="text"
															value={profileForm.username}
															disabled
															className="w-full px-4 py-3.5 bg-gray-50 border border-gray-200 rounded-xl text-gray-500 cursor-not-allowed"
														/>
														<div className="absolute inset-y-0 right-0 flex items-center pr-3">
															<div className="text-xs text-gray-400 bg-gray-200 px-2 py-1 rounded">只读</div>
														</div>
													</div>
												</div>

												<div className="space-y-2">
													<label className="block text-sm font-semibold text-gray-700">邮箱地址</label>
													<input
														type="email"
														value={profileForm.email}
														onChange={(e) => setProfileForm({ ...profileForm, email: e.target.value })}
														placeholder="请输入邮箱地址"
														className="w-full px-4 py-3.5 bg-white/80 border border-gray-200 rounded-xl focus:bg-white focus:border-blue-500 focus:ring-4 focus:ring-blue-500/10 transition-all duration-200"
													/>
												</div>

												<div className="space-y-2">
													<label className="block text-sm font-semibold text-gray-700">职位</label>
													<input
														type="text"
														value={profileForm.position}
														onChange={(e) => setProfileForm({ ...profileForm, position: e.target.value })}
														placeholder="如：运维工程师、系统管理员"
														className="w-full px-4 py-3.5 bg-white/80 border border-gray-200 rounded-xl focus:bg-white focus:border-blue-500 focus:ring-4 focus:ring-blue-500/10 transition-all duration-200"
													/>
												</div>

												<div className="space-y-2 md:col-span-2">
													{/* 个人简介已移除 */}
												</div>
											</div>

											<div className="flex justify-end pt-6 border-t border-gray-100 mt-8">
												<button
													onClick={updateProfile}
													disabled={saving}
													className="flex items-center space-x-2 px-6 py-3 bg-gradient-to-r from-blue-600 to-violet-600 hover:from-blue-700 hover:to-violet-700 disabled:from-gray-400 disabled:to-gray-500 text-white font-bold rounded-xl shadow-xl shadow-blue-500/25 hover:shadow-blue-500/40 disabled:shadow-none transition-all duration-300 transform hover:scale-[1.02] disabled:scale-100 disabled:cursor-not-allowed"
												>
													{saving ? (
														<>
															<div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
															<span>保存中...</span>
														</>
													) : (
														<>
															<Save className="w-5 h-5" />
															<span>保存资料</span>
														</>
													)}
												</button>
											</div>
										</>
									)}
								</div>
							)}

							{/* Security Tab */}
							{activeTab === 'security' && (
								<div className="p-8">
									<div className="flex items-center justify-between mb-8">
										<div>
											<h3 className="text-2xl font-bold text-gray-900">安全设置</h3>
											<p className="text-gray-600 mt-1">管理您的密码和安全选项</p>
										</div>
										<Shield className="w-6 h-6 text-gray-400" />
									</div>

									<div className="space-y-6">
										<div className="space-y-2">
											<label className="block text-sm font-semibold text-gray-700">当前密码</label>
											<div className="relative">
												<input
													type={showPasswords.old ? 'text' : 'password'}
													value={passwordForm.old_password}
													onChange={(e) => setPasswordForm({ ...passwordForm, old_password: e.target.value })}
													placeholder="请输入当前密码"
													className="w-full px-4 py-3.5 pr-12 bg-white/80 border border-gray-200 rounded-xl focus:bg-white focus:border-blue-500 focus:ring-4 focus:ring-blue-500/10 transition-all duration-200"
												/>
												<button
													type="button"
													onClick={() => setShowPasswords({ ...showPasswords, old: !showPasswords.old })}
													className="absolute right-3 top-1/2 -translate-y-1/2 p-1.5 text-gray-400 hover:text-gray-600 transition-colors duration-200 rounded-lg hover:bg-gray-100"
												>
													{showPasswords.old ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
												</button>
											</div>
										</div>

										<div className="space-y-2">
											<label className="block text-sm font-semibold text-gray-700">新密码</label>
											<div className="relative">
												<input
													type={showPasswords.new ? 'text' : 'password'}
													value={passwordForm.new_password}
													onChange={(e) => setPasswordForm({ ...passwordForm, new_password: e.target.value })}
													placeholder="请输入新密码（至少6位）"
													className="w-full px-4 py-3.5 pr-12 bg-white/80 border border-gray-200 rounded-xl focus:bg-white focus:border-blue-500 focus:ring-4 focus:ring-blue-500/10 transition-all duration-200"
												/>
												<button
													type="button"
													onClick={() => setShowPasswords({ ...showPasswords, new: !showPasswords.new })}
													className="absolute right-3 top-1/2 -translate-y-1/2 p-1.5 text-gray-400 hover:text-gray-600 transition-colors duration-200 rounded-lg hover:bg-gray-100"
												>
													{showPasswords.new ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
												</button>
											</div>
										</div>

										<div className="space-y-2">
											<label className="block text-sm font-semibold text-gray-700">确认新密码</label>
											<div className="relative">
												<input
													type={showPasswords.confirm ? 'text' : 'password'}
													value={passwordForm.confirm_password}
													onChange={(e) => setPasswordForm({ ...passwordForm, confirm_password: e.target.value })}
													placeholder="请再次输入新密码"
													className="w-full px-4 py-3.5 pr-12 bg-white/80 border border-gray-200 rounded-xl focus:bg-white focus:border-blue-500 focus:ring-4 focus:ring-blue-500/10 transition-all duration-200"
												/>
												<button
													type="button"
													onClick={() => setShowPasswords({ ...showPasswords, confirm: !showPasswords.confirm })}
													className="absolute right-3 top-1/2 -translate-y-1/2 p-1.5 text-gray-400 hover:text-gray-600 transition-colors duration-200 rounded-lg hover:bg-gray-100"
												>
													{showPasswords.confirm ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
												</button>
											</div>
										</div>
									</div>

									<div className="flex justify-end pt-6 border-t border-gray-100 mt-8">
										<button
											onClick={updatePassword}
											disabled={saving || !passwordForm.old_password || !passwordForm.new_password || !passwordForm.confirm_password}
											className="flex items-center space-x-2 px-6 py-3 bg-gradient-to-r from-red-600 to-pink-600 hover:from-red-700 hover:to-pink-700 disabled:from-gray-400 disabled:to-gray-500 text-white font-bold rounded-xl shadow-xl shadow-red-500/25 hover:shadow-red-500/40 disabled:shadow-none transition-all duration-300 transform hover:scale-[1.02] disabled:scale-100 disabled:cursor-not-allowed"
										>
											{saving ? (
												<>
													<div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
													<span>修改中...</span>
												</>
											) : (
												<>
													<Shield className="w-5 h-5" />
													<span>修改密码</span>
												</>
											)}
										</button>
									</div>
								</div>
							)}
						</div>
					</div>
				</div>
			</div>
		</div>
	)
}