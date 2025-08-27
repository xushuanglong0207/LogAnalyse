// @ts-nocheck
'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { 
	Users, 
	Plus, 
	Edit, 
	Trash2, 
	Search,
	Mail,
	Shield,
	User,
	ArrowLeft,
	Crown,
	UserCheck
} from 'lucide-react'

function computeApiBase(): string {
	if (typeof window !== 'undefined') {
		const protocol = window.location.protocol
		const host = window.location.hostname
		return `${protocol}//${host}:8001`
	}
	return ''
}

export default function UsersPage() {
	const router = useRouter()
	const [apiBase] = useState(computeApiBase())
	const [loading, setLoading] = useState(true)
	
	// 用户数据
	const [users, setUsers] = useState<any[]>([])
	const [searchQuery, setSearchQuery] = useState('')
	
	// 模态框状态
	const [userModalVisible, setUserModalVisible] = useState(false)
	const [userModalMode, setUserModalMode] = useState<'add' | 'edit'>('add')
	const [userForm, setUserForm] = useState<any>({ 
		id: null, 
		username: '', 
		email: '', 
		password: '', 
		role: '普通用户' 
	})

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

	const showToast = (message: string, type: 'success' | 'error' | 'info' = 'info') => {
		console.log(`${type}: ${message}`)
	}

	const fetchUsers = async () => { 
		try { 
			const r = await authedFetch(`${apiBase}/api/users`)
			if (r.ok) { 
				const d = await r.json()
				setUsers(d.users || []) 
			} 
		} catch (err) {
			console.error('获取用户列表失败')
		}
	}

	// 用户操作
	const openUserAdd = () => { 
		setUserForm({ 
			id: null, 
			username: '', 
			email: '', 
			password: '', 
			role: '普通用户' 
		})
		setUserModalMode('add')
		setUserModalVisible(true) 
	}

	const openUserEdit = (user: any) => { 
		setUserForm({ 
			id: user.id, 
			username: user.username, 
			email: user.email || '', 
			password: '', 
			role: user.role || '普通用户' 
		})
		setUserModalMode('edit')
		setUserModalVisible(true) 
	}

	const submitUser = async () => {
		try {
			if (userModalMode === 'add') {
				const r = await authedFetch(`${apiBase}/api/users`, { 
					method: 'POST', 
					headers: { 'Content-Type': 'application/json' }, 
					body: JSON.stringify({ 
						username: userForm.username, 
						email: userForm.email, 
						role: userForm.role, 
						password: userForm.password 
					}) 
				})
				if (!r.ok) throw new Error('创建失败')
			} else {
				const payload: any = { 
					email: userForm.email, 
					role: userForm.role 
				}
				if (userForm.password) {
					payload.password = userForm.password
				}
				
				const r = await authedFetch(`${apiBase}/api/users/${userForm.id}`, { 
					method: 'PUT', 
					headers: { 'Content-Type': 'application/json' }, 
					body: JSON.stringify(payload) 
				})
				if (!r.ok) throw new Error('更新失败')
			}
			
			setUserModalVisible(false)
			await fetchUsers()
			showToast('已保存', 'success')
		} catch (err) { 
			showToast('保存失败', 'error') 
		}
	}

	const deleteUser = async (id: number) => { 
		if (!confirm('确定删除该用户？')) return
		
		try { 
			const r = await authedFetch(`${apiBase}/api/users/${id}`, { method: 'DELETE' })
			if (r.ok) { 
				await fetchUsers()
				showToast('已删除', 'success') 
			} else {
				showToast('删除失败', 'error')
			}
		} catch (err) { 
			showToast('删除失败', 'error') 
		}
	}

	const getRoleInfo = (role: string) => {
		switch (role) {
			case '管理员':
				return { icon: Crown, color: 'text-yellow-600', bgColor: 'bg-yellow-100' }
			case '普通用户':
				return { icon: UserCheck, color: 'text-blue-600', bgColor: 'bg-blue-100' }
			default:
				return { icon: User, color: 'text-gray-600', bgColor: 'bg-gray-100' }
		}
	}

	const filteredUsers = users.filter(user => {
		if (!searchQuery) return true
		const query = searchQuery.toLowerCase()
		return (
			user.username.toLowerCase().includes(query) ||
			(user.email && user.email.toLowerCase().includes(query)) ||
			user.role.toLowerCase().includes(query)
		)
	})

	useEffect(() => {
		if (!getStoredToken()) {
			router.replace('/login')
			return
		}

		const initData = async () => {
			await fetchUsers()
			setLoading(false)
		}

		initData()
	}, [])

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
				<div className="max-w-7xl mx-auto px-4 py-4">
					<div className="flex items-center justify-between">
						<div className="flex items-center space-x-4">
							<button
								onClick={() => router.push('/')}
								className="flex items-center space-x-2 px-4 py-2 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-colors duration-200"
							>
								<ArrowLeft className="w-5 h-5" />
								<span>返回</span>
							</button>
							<div className="h-6 w-px bg-gray-300" />
							<div className="flex items-center space-x-3">
								<div className="w-10 h-10 bg-gradient-to-br from-green-500 to-emerald-600 rounded-xl flex items-center justify-center">
									<Users className="w-6 h-6 text-white" />
								</div>
								<h1 className="text-2xl font-bold text-gray-900">用户管理</h1>
							</div>
						</div>
						<div className="flex items-center space-x-2 text-sm text-gray-600">
							<Users className="w-4 h-4" />
							<span>{users.length} 位用户</span>
						</div>
					</div>
				</div>
			</header>

			<div className="max-w-7xl mx-auto px-4 py-8 space-y-6">
				{/* Search and Add */}
				<div className="bg-white/70 backdrop-blur-xl rounded-2xl shadow-xl border border-white/50 p-6">
					<div className="flex flex-col md:flex-row md:items-center md:justify-between space-y-4 md:space-y-0 md:space-x-4">
						<div className="relative flex-1">
							<Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
							<input
								placeholder="搜索用户名、邮箱或角色..."
								value={searchQuery}
								onChange={(e) => setSearchQuery(e.target.value)}
								className="w-full pl-10 pr-4 py-3 border border-gray-200 rounded-xl focus:ring-4 focus:ring-green-500/10 focus:border-green-500 transition-all duration-200"
							/>
						</div>
						<button
							onClick={openUserAdd}
							className="px-6 py-3 bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-700 hover:to-emerald-700 text-white font-medium rounded-xl shadow-lg hover:shadow-xl transition-all duration-200 flex items-center space-x-2"
						>
							<Plus className="w-5 h-5" />
							<span>添加用户</span>
						</button>
					</div>
				</div>

				{/* Users List */}
				<div className="bg-white/70 backdrop-blur-xl rounded-2xl shadow-xl border border-white/50 overflow-hidden">
					{filteredUsers.length > 0 ? (
						<>
							{/* Table Header */}
							<div className="bg-gray-50/80 border-b border-gray-100">
								<div className="grid grid-cols-12 gap-4 px-6 py-4 text-sm font-semibold text-gray-700">
									<div className="col-span-3">用户信息</div>
									<div className="col-span-3">邮箱地址</div>
									<div className="col-span-2">用户角色</div>
									<div className="col-span-2">创建时间</div>
									<div className="col-span-2 text-center">操作</div>
								</div>
							</div>
							
							{/* Table Body */}
							<div className="divide-y divide-gray-100">
								{filteredUsers.map((user) => {
									const roleInfo = getRoleInfo(user.role)
									return (
										<div key={user.id} className="grid grid-cols-12 gap-4 px-6 py-4 hover:bg-gray-50/50 transition-colors duration-200">
											<div className="col-span-3 flex items-center space-x-3">
												<div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-full flex items-center justify-center">
													<User className="w-5 h-5 text-white" />
												</div>
												<div>
													<p className="font-medium text-gray-900">{user.username}</p>
													<p className="text-sm text-gray-500">ID: {user.id}</p>
												</div>
											</div>
											<div className="col-span-3 flex items-center">
												{user.email ? (
													<div className="flex items-center space-x-2 text-gray-700">
														<Mail className="w-4 h-4 text-gray-400" />
														<span>{user.email}</span>
													</div>
												) : (
													<span className="text-gray-400 text-sm">未设置邮箱</span>
												)}
											</div>
											<div className="col-span-2 flex items-center">
												<div className={`inline-flex items-center px-3 py-1 ${roleInfo.bgColor} ${roleInfo.color} rounded-full text-sm font-medium`}>
													<roleInfo.icon className="w-4 h-4 mr-1" />
													{user.role}
												</div>
											</div>
											<div className="col-span-2 flex items-center">
												<span className="text-sm text-gray-600">
													{user.created_at ? new Date(user.created_at).toLocaleDateString() : '-'}
												</span>
											</div>
											<div className="col-span-2 flex items-center justify-center space-x-2">
												<button
													onClick={() => openUserEdit(user)}
													className="px-3 py-1.5 bg-blue-100 hover:bg-blue-200 text-blue-600 rounded-lg text-sm font-medium transition-colors duration-200 flex items-center space-x-1"
												>
													<Edit className="w-3 h-3" />
													<span>编辑</span>
												</button>
												<button
													onClick={() => deleteUser(user.id)}
													className="px-3 py-1.5 bg-red-100 hover:bg-red-200 text-red-600 rounded-lg text-sm font-medium transition-colors duration-200 flex items-center space-x-1"
												>
													<Trash2 className="w-3 h-3" />
													<span>删除</span>
												</button>
											</div>
										</div>
									)
								})}
							</div>
						</>
					) : (
						<div className="p-12 text-center">
							<div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
								<Users className="w-8 h-8 text-gray-400" />
							</div>
							<p className="text-gray-500 font-medium mb-2">
								{searchQuery ? '未找到匹配的用户' : '暂无用户'}
							</p>
							<p className="text-gray-400 text-sm">
								{searchQuery ? '尝试调整搜索条件' : '添加第一个用户'}
							</p>
						</div>
					)}
				</div>
			</div>

			{/* User Modal */}
			{userModalVisible && (
				<div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
					<div className="bg-white rounded-2xl shadow-2xl max-w-md w-full">
						<div className="p-6 border-b border-gray-100">
							<h3 className="text-lg font-bold text-gray-900">
								{userModalMode === 'add' ? '添加用户' : '编辑用户'}
							</h3>
						</div>
						<div className="p-6 space-y-4">
							<div className="space-y-2">
								<label className="block text-sm font-medium text-gray-700">用户名*</label>
								<input
									value={userForm.username}
									onChange={(e) => setUserForm({ ...userForm, username: e.target.value })}
									disabled={userModalMode === 'edit'}
									className={`w-full px-3 py-2 border border-gray-200 rounded-lg transition-all duration-200 ${
										userModalMode === 'edit' 
											? 'bg-gray-50 text-gray-500 cursor-not-allowed' 
											: 'focus:ring-4 focus:ring-green-500/10 focus:border-green-500'
									}`}
								/>
								{userModalMode === 'edit' && (
									<p className="text-xs text-gray-500">用户名创建后不可修改</p>
								)}
							</div>
							
							<div className="space-y-2">
								<label className="block text-sm font-medium text-gray-700">邮箱地址</label>
								<input
									type="email"
									value={userForm.email}
									onChange={(e) => setUserForm({ ...userForm, email: e.target.value })}
									className="w-full px-3 py-2 border border-gray-200 rounded-lg focus:ring-4 focus:ring-green-500/10 focus:border-green-500 transition-all duration-200"
								/>
							</div>
							
							<div className="space-y-2">
								<label className="block text-sm font-medium text-gray-700">用户角色*</label>
								<select
									value={userForm.role}
									onChange={(e) => setUserForm({ ...userForm, role: e.target.value })}
									className="w-full px-3 py-2 border border-gray-200 rounded-lg focus:ring-4 focus:ring-green-500/10 focus:border-green-500 transition-all duration-200"
								>
									<option value="管理员">管理员</option>
									<option value="普通用户">普通用户</option>
								</select>
							</div>
							
							<div className="space-y-2">
								<label className="block text-sm font-medium text-gray-700">
									{userModalMode === 'add' ? '密码*' : '新密码（留空不修改）'}
								</label>
								<input
									type="password"
									value={userForm.password}
									onChange={(e) => setUserForm({ ...userForm, password: e.target.value })}
									className="w-full px-3 py-2 border border-gray-200 rounded-lg focus:ring-4 focus:ring-green-500/10 focus:border-green-500 transition-all duration-200"
								/>
							</div>
						</div>
						<div className="p-6 border-t border-gray-100 flex justify-end space-x-3">
							<button
								onClick={() => setUserModalVisible(false)}
								className="px-4 py-2 text-gray-600 hover:text-gray-800 hover:bg-gray-100 rounded-lg transition-colors duration-200"
							>
								取消
							</button>
							<button
								onClick={submitUser}
								disabled={!userForm.username || (userModalMode === 'add' && !userForm.password)}
								className="px-6 py-2 bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-700 hover:to-emerald-700 disabled:from-gray-400 disabled:to-gray-500 text-white font-medium rounded-lg shadow-lg hover:shadow-xl disabled:shadow-none transition-all duration-200 disabled:cursor-not-allowed"
							>
								{userModalMode === 'add' ? '创建用户' : '更新用户'}
							</button>
						</div>
					</div>
				</div>
			)}
		</div>
	)
}