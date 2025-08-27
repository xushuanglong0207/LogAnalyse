// @ts-nocheck
'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { 
	TrendingUp, 
	FileText, 
	Shield, 
	Database, 
	ArrowLeft,
	BarChart3,
	Activity,
	Users
} from 'lucide-react'

function computeApiBase(): string {
	if (typeof window !== 'undefined') {
		const protocol = window.location.protocol
		const host = window.location.hostname
		return `${protocol}//${host}:8001`
	}
	return ''
}

export default function DashboardPage() {
	const router = useRouter()
	const [apiBase] = useState(computeApiBase())
	const [loading, setLoading] = useState(true)
	const [currentUser, setCurrentUser] = useState<any>(null)
	const [dashboardStats, setDashboardStats] = useState<any>({ 
		uploaded_files: 0, 
		detected_issues: 0, 
		detection_rules: 7, 
		recent_activity: [] 
	})
	const [analysisResults, setAnalysisResults] = useState<any[]>([])

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
			}
		} catch (err) {
			console.error('获取用户信息失败')
		}
	}

	const fetchDashboardStats = async () => {
		try { 
			const r = await authedFetch(`${apiBase}/api/dashboard/stats`)
			if (r.ok) setDashboardStats(await r.json())
		} catch (err) {
			console.error('获取统计数据失败')
		}
	}

	const fetchAnalysisResults = async () => { 
		try { 
			const r = await authedFetch(`${apiBase}/api/analysis/results`)
			if (r.ok) { 
				const d = await r.json()
				setAnalysisResults(d.results || []) 
			} 
		} catch (err) {
			console.error('获取分析结果失败')
		}
	}

	const openAnalysisDetail = async (fileId: number, filename: string) => {
		try { 
			const r = await authedFetch(`${apiBase}/api/analysis/${fileId}`)
			if (r.ok) { 
				const d = await r.json()
				// 这里可以打开详情模态框或跳转到详情页面
				console.log('分析详情:', d)
			} 
		} catch (err) {
			console.error('详情加载失败')
		}
	}

	useEffect(() => {
		if (!getStoredToken()) {
			router.replace('/login')
			return
		}

		const initData = async () => {
			await Promise.all([
				fetchCurrentUser(),
				fetchDashboardStats(),
				fetchAnalysisResults()
			])
			setLoading(false)
		}

		initData()
	}, [])

	if (loading) {
		return (
			<div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-100 flex items-center justify-center">
				<div className="text-center">
					<div className="w-16 h-16 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
					<p className="text-gray-600">加载数据中...</p>
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
								<div className="w-10 h-10 bg-gradient-to-br from-blue-600 to-violet-600 rounded-xl flex items-center justify-center">
									<BarChart3 className="w-6 h-6 text-white" />
								</div>
								<h1 className="text-2xl font-bold text-gray-900">系统仪表板</h1>
							</div>
						</div>
						{currentUser && (
							<div className="flex items-center space-x-3">
								<span className="text-gray-600">Hi,</span>
								<span className="font-bold text-gray-900">{currentUser.username}</span>
							</div>
						)}
					</div>
				</div>
			</header>

			<div className="max-w-7xl mx-auto px-4 py-8">
				{/* Stats Cards */}
				<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
					{[
						{ 
							icon: FileText, 
							color: 'from-emerald-500 to-teal-600', 
							value: dashboardStats.uploaded_files, 
							label: '已上传文件',
							bgColor: 'bg-emerald-50',
							textColor: 'text-emerald-600'
						},
						{ 
							icon: Shield, 
							color: 'from-red-500 to-pink-600', 
							value: dashboardStats.detected_issues, 
							label: '检测到错误',
							bgColor: 'bg-red-50',
							textColor: 'text-red-600'
						},
						{ 
							icon: Activity, 
							color: 'from-blue-500 to-indigo-600', 
							value: dashboardStats.detection_rules, 
							label: '检测规则',
							bgColor: 'bg-blue-50',
							textColor: 'text-blue-600'
						},
						{ 
							icon: Database, 
							color: 'from-violet-500 to-purple-600', 
							value: analysisResults.length, 
							label: '分析结果',
							bgColor: 'bg-violet-50',
							textColor: 'text-violet-600'
						}
					].map((stat, index) => (
						<div key={index} className="bg-white/70 backdrop-blur-xl rounded-2xl shadow-xl border border-white/50 p-6 hover:shadow-2xl transition-all duration-300 hover:scale-105">
							<div className="flex items-center justify-between mb-4">
								<div className={`w-12 h-12 rounded-xl ${stat.bgColor} flex items-center justify-center`}>
									<stat.icon className={`w-6 h-6 ${stat.textColor}`} />
								</div>
								<TrendingUp className="w-5 h-5 text-gray-400" />
							</div>
							<div className="space-y-1">
								<p className="text-3xl font-bold text-gray-900">{stat.value}</p>
								<p className="text-gray-600 font-medium">{stat.label}</p>
							</div>
						</div>
					))}
				</div>

				{/* Recent Analysis Results */}
				<div className="bg-white/70 backdrop-blur-xl rounded-2xl shadow-xl border border-white/50 overflow-hidden">
					<div className="p-6 border-b border-gray-100">
						<div className="flex items-center justify-between">
							<div className="flex items-center space-x-3">
								<div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-lg flex items-center justify-center">
									<Activity className="w-4 h-4 text-white" />
								</div>
								<h2 className="text-xl font-bold text-gray-900">最近分析结果</h2>
							</div>
							<span className="text-sm text-gray-500">双击查看详情</span>
						</div>
					</div>

					<div className="max-h-96 overflow-auto">
						{analysisResults.length > 0 ? (
							<div className="divide-y divide-gray-100">
								{analysisResults.slice(-20).reverse().map((result, index) => (
									<div 
										key={index} 
										onDoubleClick={() => openAnalysisDetail(result.file_id, result.filename)}
										className="p-4 hover:bg-gray-50/50 cursor-pointer transition-colors duration-200 group"
									>
										<div className="flex items-center justify-between">
											<div className="flex-1">
												<h3 className="font-semibold text-gray-900 group-hover:text-blue-600 transition-colors duration-200">
													{result.filename}
												</h3>
												<p className="text-gray-600 text-sm mt-1">
													发现 <span className="font-medium text-red-600">{result.summary?.total_issues || 0}</span> 个问题
													{result.analysis_time && (
														<span className="ml-2">• {new Date(result.analysis_time).toLocaleString()}</span>
													)}
												</p>
											</div>
											<div className="ml-4">
												<div className={`px-3 py-1 rounded-full text-xs font-medium ${
													result.summary?.total_issues > 0 
														? 'bg-red-100 text-red-600' 
														: 'bg-green-100 text-green-600'
												}`}>
													{result.summary?.total_issues > 0 ? '有问题' : '正常'}
												</div>
											</div>
										</div>
									</div>
								))}
							</div>
						) : (
							<div className="p-8 text-center">
								<div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
									<Activity className="w-8 h-8 text-gray-400" />
								</div>
								<p className="text-gray-500 font-medium">暂无分析记录</p>
								<p className="text-gray-400 text-sm mt-1">上传日志文件开始分析</p>
							</div>
						)}
					</div>
				</div>
			</div>
		</div>
	)
}