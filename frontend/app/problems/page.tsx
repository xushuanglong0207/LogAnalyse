// @ts-nocheck
'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { 
	BookOpen, 
	Plus, 
	Edit, 
	Trash2, 
	Search,
	Filter,
	ExternalLink,
	ArrowLeft,
	Database,
	Tag,
	BarChart3
} from 'lucide-react'

function computeApiBase(): string {
	if (typeof window !== 'undefined') {
		const protocol = window.location.protocol
		const host = window.location.hostname
		return `${protocol}//${host}:8001`
	}
	return ''
}

export default function ProblemsPage() {
	const router = useRouter()
	const [apiBase] = useState(computeApiBase())
	const [loading, setLoading] = useState(true)
	
	// 问题库数据
	const [problems, setProblems] = useState<any[]>([])
	const [problemStatsByType, setProblemStatsByType] = useState<Record<string, number>>({})
	
	// 筛选条件
	const [problemFilterType, setProblemFilterType] = useState<string>('')
	const [problemFilterQuery, setProblemFilterQuery] = useState<string>('')
	const [statsExpanded, setStatsExpanded] = useState(false)
	
	// 分页
	const [problemPage, setProblemPage] = useState(1)
	const PROBLEM_PAGE_SIZE = 20
	
	// 模态框状态
	const [problemModalVisible, setProblemModalVisible] = useState(false)
	const [problemForm, setProblemForm] = useState<any>({ 
		id: null, 
		title: '', 
		url: '', 
		error_type: '' 
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

	const fetchProblems = async (type: string = problemFilterType, q: string = problemFilterQuery) => {
		try {
			const params = new URLSearchParams()
			if (type) params.set('error_type', type)
			if (q) params.set('q', q)
			const r = await authedFetch(`${apiBase}/api/problems?${params.toString()}`)
			if (r.ok) { 
				const d = await r.json()
				setProblems(d.problems || [])
				setProblemPage(1)
			}
		} catch (err) {
			console.error('获取问题库失败')
		}
	}

	const fetchProblemStats = async () => {
		try {
			const r = await authedFetch(`${apiBase}/api/problems/stats`)
			if (r.ok) { 
				const d = await r.json()
				setProblemStatsByType(d.by_type || {}) 
			}
		} catch (err) {
			console.error('获取统计数据失败')
		}
	}

	// 工具函数
	const sanitizeUrl = (s: string): string => {
		try { 
			const m = String(s || '').match(/https?:\/\/[^\s<>"']+/i)
			return m ? m[0] : '' 
		} catch { 
			return '' 
		}
	}

	const removeUrls = (s: string): string => {
		try { 
			return String(s || '').replace(/https?:\/\/[^\s<>"']+/ig, '').trim() 
		} catch { 
			return s 
		}
	}

	const titleFromUrl = (u: string): string => {
		try { 
			const url = new URL(u)
			const segs = url.pathname.split('/').filter(Boolean)
			const last = segs[segs.length - 1] || url.hostname
			return decodeURIComponent(last) 
		} catch { 
			return u 
		}
	}

	// 问题操作
	const openProblemAdd = () => { 
		setProblemForm({ 
			id: null, 
			title: '', 
			url: '', 
			error_type: problemFilterType || '' 
		})
		setProblemModalVisible(true) 
	}

	const openProblemEdit = (p: any) => { 
		setProblemForm({ 
			id: p.id, 
			title: p.title, 
			url: p.url, 
			error_type: p.error_type 
		})
		setProblemModalVisible(true) 
	}

	const submitProblem = async () => {
		try {
			// 统一清洗：名称去掉链接，链接只保留URL；若名称为空用URL生成
			const cleanedUrl = sanitizeUrl(problemForm.url || '') || sanitizeUrl(problemForm.title || '')
			let cleanedTitle = removeUrls(problemForm.title || '')
			if (!cleanedTitle) cleanedTitle = cleanedUrl ? titleFromUrl(cleanedUrl) : '未命名问题'
			
			const payload = { 
				title: cleanedTitle, 
				url: cleanedUrl, 
				error_type: problemForm.error_type 
			}
			if (!payload.url) { 
				showToast('请填写有效链接', 'error')
				return 
			}
			
			let r
			if (problemForm.id) {
				r = await authedFetch(`${apiBase}/api/problems/${problemForm.id}`, { 
					method: 'PUT', 
					headers: { 'Content-Type': 'application/json' }, 
					body: JSON.stringify(payload) 
				})
			} else {
				r = await authedFetch(`${apiBase}/api/problems`, { 
					method: 'POST', 
					headers: { 'Content-Type': 'application/json' }, 
					body: JSON.stringify(payload) 
				})
			}
			
			if (r.ok) { 
				setProblemModalVisible(false)
				await Promise.all([
					fetchProblems(problemFilterType, problemFilterQuery), 
					fetchProblemStats()
				])
				showToast('问题已保存', 'success') 
			} else {
				showToast('保存失败', 'error')
			}
		} catch (err) { 
			showToast('保存失败', 'error') 
		}
	}

	const deleteProblem = async (id: number) => { 
		if (!confirm('确定删除该问题？')) return
		
		try { 
			const r = await authedFetch(`${apiBase}/api/problems/${id}`, { method: 'DELETE' })
			if (r.ok) { 
				await Promise.all([
					fetchProblems(problemFilterType, problemFilterQuery), 
					fetchProblemStats()
				])
				showToast('已删除', 'success') 
			} else {
				showToast('删除失败', 'error')
			}
		} catch (err) { 
			showToast('删除失败', 'error') 
		}
	}

	const clearFilters = () => {
		setProblemFilterType('')
		setProblemFilterQuery('')
		fetchProblems('', '')
		fetchProblemStats()
	}

	const totalProblems = Object.values(problemStatsByType).reduce((a, b) => a + b, 0)
	const currentProblems = problems.slice((problemPage - 1) * PROBLEM_PAGE_SIZE, problemPage * PROBLEM_PAGE_SIZE)
	const totalPages = Math.ceil(problems.length / PROBLEM_PAGE_SIZE)

	useEffect(() => {
		if (!getStoredToken()) {
			router.replace('/login')
			return
		}

		const initData = async () => {
			await Promise.all([
				fetchProblems(),
				fetchProblemStats()
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
								<div className="w-10 h-10 bg-gradient-to-br from-purple-500 to-indigo-600 rounded-xl flex items-center justify-center">
									<BookOpen className="w-6 h-6 text-white" />
								</div>
								<h1 className="text-2xl font-bold text-gray-900">问题库</h1>
							</div>
						</div>
						<div className="flex items-center space-x-2 text-sm text-gray-600">
							<Database className="w-4 h-4" />
							<span>{totalProblems} 个问题</span>
						</div>
					</div>
				</div>
			</header>

			<div className="max-w-7xl mx-auto px-4 py-8 space-y-6">
				{/* Search and Filters */}
				<div className="bg-white/70 backdrop-blur-xl rounded-2xl shadow-xl border border-white/50 p-6">
					<div className="flex flex-col lg:flex-row lg:items-center lg:justify-between space-y-4 lg:space-y-0 lg:space-x-4">
						<div className="flex-1 relative">
							<Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
							<input
								placeholder="搜索问题（名称/链接/类型）"
								value={problemFilterQuery}
								onChange={(e) => setProblemFilterQuery(e.target.value)}
								className="w-full pl-10 pr-4 py-3 border border-gray-200 rounded-xl focus:ring-4 focus:ring-purple-500/10 focus:border-purple-500 transition-all duration-200"
							/>
						</div>
						<div className="flex items-center space-x-3">
							<button
								onClick={() => fetchProblems('', problemFilterQuery)}
								className="px-4 py-3 bg-purple-100 hover:bg-purple-200 text-purple-600 rounded-xl font-medium transition-colors duration-200 flex items-center space-x-2"
							>
								<Search className="w-4 h-4" />
								<span>搜索</span>
							</button>
							<button
								onClick={clearFilters}
								className="px-4 py-3 bg-gray-100 hover:bg-gray-200 text-gray-600 rounded-xl font-medium transition-colors duration-200 flex items-center space-x-2"
							>
								<Filter className="w-4 h-4" />
								<span>清空</span>
							</button>
							<button
								onClick={openProblemAdd}
								className="px-6 py-3 bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-700 hover:to-indigo-700 text-white font-medium rounded-xl shadow-lg hover:shadow-xl transition-all duration-200 flex items-center space-x-2"
							>
								<Plus className="w-5 h-5" />
								<span>新增问题</span>
							</button>
						</div>
					</div>
				</div>

				{/* Statistics */}
				<div className="bg-white/70 backdrop-blur-xl rounded-2xl shadow-xl border border-white/50 p-6">
					<div className="flex items-center justify-between mb-4">
						<h3 className="text-lg font-bold text-gray-900 flex items-center">
							<BarChart3 className="w-5 h-5 mr-2 text-purple-600" />
							分类统计
						</h3>
						<button
							onClick={() => setStatsExpanded(v => !v)}
							className="text-sm text-purple-600 hover:text-purple-700 font-medium"
						>
							{statsExpanded ? '收起' : '展开'}
						</button>
					</div>
					
					<div className={`grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3 ${statsExpanded ? '' : 'max-h-20 overflow-hidden'}`}>
						<button
							onClick={() => {
								setProblemFilterType('')
								fetchProblems('', problemFilterQuery)
							}}
							className={`p-3 rounded-xl text-left transition-all duration-200 ${
								!problemFilterType ? 'bg-purple-100 text-purple-700 shadow-md' : 'bg-gray-50 hover:bg-gray-100 text-gray-700'
							}`}
						>
							<div className="text-lg font-bold">{totalProblems}</div>
							<div className="text-sm">全部</div>
						</button>
						
						{Object.entries(problemStatsByType).map(([type, count]) => (
							<button
								key={type}
								onClick={() => {
									setProblemFilterType(type)
									fetchProblems(type, problemFilterQuery)
								}}
								className={`p-3 rounded-xl text-left transition-all duration-200 ${
									problemFilterType === type ? 'bg-purple-100 text-purple-700 shadow-md' : 'bg-gray-50 hover:bg-gray-100 text-gray-700'
								}`}
							>
								<div className="text-lg font-bold">{count}</div>
								<div className="text-sm truncate" title={type}>{type}</div>
							</button>
						))}
					</div>
				</div>

				{/* Problems List */}
				<div className="bg-white/70 backdrop-blur-xl rounded-2xl shadow-xl border border-white/50 overflow-hidden">
					{/* Table Header */}
					<div className="bg-gray-50/80 border-b border-gray-100">
						<div className="grid grid-cols-12 gap-4 px-6 py-4 text-sm font-semibold text-gray-700">
							<div className="col-span-4">问题名称</div>
							<div className="col-span-4">问题链接</div>
							<div className="col-span-2">错误类型</div>
							<div className="col-span-2 text-center">操作</div>
						</div>
					</div>
					
					{/* Table Body */}
					{currentProblems.length > 0 ? (
						<div className="divide-y divide-gray-100">
							{currentProblems.map((problem) => (
								<div key={problem.id} className="grid grid-cols-12 gap-4 px-6 py-4 hover:bg-gray-50/50 transition-colors duration-200">
									<div className="col-span-4">
										<p className="font-medium text-gray-900 truncate" title={problem.title}>
											{problem.title}
										</p>
									</div>
									<div className="col-span-4">
										<a
											href={problem.url}
											target="_blank"
											rel="noopener noreferrer"
											className="text-purple-600 hover:text-purple-700 truncate flex items-center space-x-1 group"
											title={problem.url}
										>
											<span className="truncate">{problem.url}</span>
											<ExternalLink className="w-3 h-3 opacity-0 group-hover:opacity-100 transition-opacity duration-200 flex-shrink-0" />
										</a>
									</div>
									<div className="col-span-2">
										<div className="inline-flex items-center px-2 py-1 bg-gray-100 text-gray-700 rounded-full text-xs font-medium">
											<Tag className="w-3 h-3 mr-1" />
											<span className="truncate" title={problem.error_type}>{problem.error_type}</span>
										</div>
									</div>
									<div className="col-span-2 flex items-center justify-center space-x-2">
										<button
											onClick={() => openProblemEdit(problem)}
											className="px-3 py-1.5 bg-blue-100 hover:bg-blue-200 text-blue-600 rounded-lg text-sm font-medium transition-colors duration-200 flex items-center space-x-1"
										>
											<Edit className="w-3 h-3" />
											<span>编辑</span>
										</button>
										<button
											onClick={() => deleteProblem(problem.id)}
											className="px-3 py-1.5 bg-red-100 hover:bg-red-200 text-red-600 rounded-lg text-sm font-medium transition-colors duration-200 flex items-center space-x-1"
										>
											<Trash2 className="w-3 h-3" />
											<span>删除</span>
										</button>
									</div>
								</div>
							))}
						</div>
					) : (
						<div className="p-12 text-center">
							<div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
								<BookOpen className="w-8 h-8 text-gray-400" />
							</div>
							<p className="text-gray-500 font-medium mb-2">暂无问题记录</p>
							<p className="text-gray-400 text-sm">添加第一个问题到知识库</p>
						</div>
					)}

					{/* Pagination */}
					{totalPages > 1 && (
						<div className="bg-gray-50/80 border-t border-gray-100 px-6 py-4">
							<div className="flex items-center justify-between">
								<button
									onClick={() => setProblemPage(p => Math.max(1, p - 1))}
									disabled={problemPage <= 1}
									className="px-4 py-2 bg-white hover:bg-gray-50 disabled:bg-gray-100 text-gray-700 disabled:text-gray-400 border border-gray-200 rounded-lg font-medium transition-colors duration-200 disabled:cursor-not-allowed"
								>
									上一页
								</button>
								<span className="text-sm text-gray-600">
									第 {problemPage} / {totalPages} 页 · 共 {problems.length} 条记录
								</span>
								<button
									onClick={() => setProblemPage(p => Math.min(totalPages, p + 1))}
									disabled={problemPage >= totalPages}
									className="px-4 py-2 bg-white hover:bg-gray-50 disabled:bg-gray-100 text-gray-700 disabled:text-gray-400 border border-gray-200 rounded-lg font-medium transition-colors duration-200 disabled:cursor-not-allowed"
								>
									下一页
								</button>
							</div>
						</div>
					)}
				</div>
			</div>

			{/* Problem Modal */}
			{problemModalVisible && (
				<div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
					<div className="bg-white rounded-2xl shadow-2xl max-w-2xl w-full">
						<div className="p-6 border-b border-gray-100">
							<h3 className="text-lg font-bold text-gray-900">
								{problemForm.id ? '编辑问题' : '新增问题'}
							</h3>
						</div>
						<div className="p-6 space-y-4">
							<div className="space-y-2">
								<label className="block text-sm font-medium text-gray-700">问题名称*</label>
								<input
									value={problemForm.title}
									onChange={(e) => {
										const v = e.target.value
										const detected = sanitizeUrl(v)
										setProblemForm({ 
											...problemForm, 
											title: removeUrls(v), 
											url: detected || problemForm.url 
										})
									}}
									className="w-full px-3 py-2 border border-gray-200 rounded-lg focus:ring-4 focus:ring-purple-500/10 focus:border-purple-500 transition-all duration-200"
								/>
							</div>
							
							<div className="space-y-2">
								<label className="block text-sm font-medium text-gray-700">问题链接*</label>
								<input
									value={problemForm.url}
									onChange={(e) => setProblemForm({ ...problemForm, url: e.target.value })}
									onBlur={(e) => {
										const link = sanitizeUrl(e.target.value)
										setProblemForm({ 
											...problemForm, 
											url: link, 
											title: (problemForm.title ? removeUrls(problemForm.title) : titleFromUrl(link)) 
										})
									}}
									placeholder="https://..."
									className="w-full px-3 py-2 border border-gray-200 rounded-lg focus:ring-4 focus:ring-purple-500/10 focus:border-purple-500 transition-all duration-200"
								/>
							</div>
							
							<div className="space-y-2">
								<label className="block text-sm font-medium text-gray-700">问题类型*</label>
								<input
									value={problemForm.error_type}
									onChange={(e) => setProblemForm({ ...problemForm, error_type: e.target.value })}
									placeholder="如: OutOfMemoryError, NetworkTimeout"
									className="w-full px-3 py-2 border border-gray-200 rounded-lg focus:ring-4 focus:ring-purple-500/10 focus:border-purple-500 transition-all duration-200"
								/>
							</div>
						</div>
						<div className="p-6 border-t border-gray-100 flex justify-end space-x-3">
							<button
								onClick={() => setProblemModalVisible(false)}
								className="px-4 py-2 text-gray-600 hover:text-gray-800 hover:bg-gray-100 rounded-lg transition-colors duration-200"
							>
								取消
							</button>
							<button
								onClick={submitProblem}
								disabled={!problemForm.title || !problemForm.url || !problemForm.error_type}
								className="px-6 py-2 bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-700 hover:to-indigo-700 disabled:from-gray-400 disabled:to-gray-500 text-white font-medium rounded-lg shadow-lg hover:shadow-xl disabled:shadow-none transition-all duration-200 disabled:cursor-not-allowed"
							>
								保存
							</button>
						</div>
					</div>
				</div>
			)}
		</div>
	)
}