// @ts-nocheck
'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { 
	Search, 
	Plus, 
	Edit, 
	Trash2, 
	Power,
	Folder,
	ArrowLeft,
	Shield,
	Settings,
	FileText
} from 'lucide-react'

function computeApiBase(): string {
	if (typeof window !== 'undefined') {
		const protocol = window.location.protocol
		const host = window.location.hostname
		return `${protocol}//${host}:8001`
	}
	return ''
}

export default function RulesPage() {
	const router = useRouter()
	const [apiBase] = useState(computeApiBase())
	const [loading, setLoading] = useState(true)
	
	// 规则和文件夹数据
	const [detectionRules, setDetectionRules] = useState<any[]>([])
	const [ruleFolders, setRuleFolders] = useState<any[]>([])
	const [selectedFolderId, setSelectedFolderId] = useState<number | null>(null)
	const [searchRule, setSearchRule] = useState('')
	
	// 模态框状态
	const [ruleModalVisible, setRuleModalVisible] = useState(false)
	const [ruleModalMode, setRuleModalMode] = useState<'add' | 'edit'>('add')
	const [ruleForm, setRuleForm] = useState<any>({ 
		id: null, 
		name: '', 
		description: '', 
		enabled: true, 
		patterns: '', 
		operator: 'OR', 
		is_regex: true, 
		folder_id: 1 
	})
	
	const [folderModalVisible, setFolderModalVisible] = useState(false)
	const [folderForm, setFolderForm] = useState<any>({ id: null, name: '' })

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

	const fetchDetectionRules = async (q = '', folderId: number | null = null) => { 
		try { 
			const params = new URLSearchParams()
			if (q) params.set('query', q)
			if (folderId !== null) params.set('folder_id', String(folderId))
			const r = await authedFetch(`${apiBase}/api/rules?${params.toString()}`)
			if (r.ok) { 
				const d = await r.json()
				setDetectionRules(d.rules || []) 
			} 
		} catch (err) {
			console.error('获取规则失败')
		}
	}

	const fetchRuleFolders = async () => { 
		try { 
			const r = await authedFetch(`${apiBase}/api/rule-folders`)
			if (r.ok) { 
				const d = await r.json()
				setRuleFolders(d.folders || [])
				if (d.folders && d.folders.length && selectedFolderId === null) {
					setSelectedFolderId(d.folders[0].id)
				}
			} 
		} catch (err) {
			console.error('获取文件夹失败')
		}
	}

	const parsePatterns = (s: string) => (s || '').split(/\r?\n|,|;|、/).map(v => v.trim()).filter(Boolean)

	// 规则操作
	const openRuleAdd = () => { 
		setRuleForm({ 
			id: null, 
			name: '', 
			description: '', 
			enabled: true, 
			patterns: '', 
			operator: 'OR', 
			is_regex: true, 
			folder_id: ruleFolders[0]?.id || 1 
		})
		setRuleModalMode('add')
		setRuleModalVisible(true) 
	}

	const openRuleEdit = (rule: any) => { 
		setRuleForm({ 
			id: rule.id, 
			name: rule.name, 
			description: rule.description || '', 
			enabled: !!rule.enabled, 
			patterns: (rule.patterns || []).join('\n'), 
			operator: rule.operator || 'OR', 
			is_regex: !!rule.is_regex, 
			folder_id: rule.folder_id || 1 
		})
		setRuleModalMode('edit')
		setRuleModalVisible(true) 
	}

	const submitRule = async () => {
		try {
			const payload = { 
				name: ruleForm.name, 
				description: ruleForm.description || '', 
				enabled: !!ruleForm.enabled, 
				patterns: parsePatterns(ruleForm.patterns), 
				operator: (ruleForm.operator || 'OR'), 
				is_regex: !!ruleForm.is_regex, 
				folder_id: ruleForm.folder_id || 1 
			}
			let r
			if (ruleModalMode === 'add') {
				r = await authedFetch(`${apiBase}/api/rules`, { 
					method: 'POST', 
					headers: { 'Content-Type': 'application/json' }, 
					body: JSON.stringify(payload) 
				})
			} else {
				r = await authedFetch(`${apiBase}/api/rules/${ruleForm.id}`, { 
					method: 'PUT', 
					headers: { 'Content-Type': 'application/json' }, 
					body: JSON.stringify(payload) 
				})
			}
			if (r.ok) { 
				setRuleModalVisible(false)
				await fetchDetectionRules(searchRule, selectedFolderId)
				await fetchRuleFolders()
				showToast('保存成功', 'success') 
			} else {
				showToast('保存失败', 'error')
			}
		} catch (err) { 
			showToast('保存失败', 'error') 
		}
	}

	const deleteRule = async (ruleId: number) => { 
		if (!confirm('确定删除该规则？')) return
		
		try { 
			const r = await authedFetch(`${apiBase}/api/rules/${ruleId}`, { method: 'DELETE' })
			if (r.ok) { 
				await fetchDetectionRules(searchRule, selectedFolderId)
				await fetchRuleFolders()
				showToast('删除成功', 'success') 
			} else {
				showToast('删除失败', 'error')
			}
		} catch (err) { 
			showToast('删除失败', 'error') 
		}
	}

	const toggleRule = async (ruleId: number, enabled: boolean) => { 
		try { 
			const r = await authedFetch(`${apiBase}/api/rules/${ruleId}`, { 
				method: 'PUT', 
				headers: { 'Content-Type': 'application/json' }, 
				body: JSON.stringify({ enabled: !enabled }) 
			})
			if (r.ok) { 
				await fetchDetectionRules(searchRule, selectedFolderId)
				showToast(!enabled ? '已启用' : '已禁用', 'success') 
			} 
		} catch (err) {
			showToast('操作失败', 'error')
		}
	}

	// 文件夹操作
	const submitFolder = async () => { 
		try { 
			if (folderForm.id) { 
				await authedFetch(`${apiBase}/api/rule-folders/${folderForm.id}`, { 
					method: 'PUT', 
					headers: { 'Content-Type': 'application/json' }, 
					body: JSON.stringify({ name: folderForm.name }) 
				}) 
			} else { 
				await authedFetch(`${apiBase}/api/rule-folders`, { 
					method: 'POST', 
					headers: { 'Content-Type': 'application/json' }, 
					body: JSON.stringify({ name: folderForm.name }) 
				}) 
			} 
			setFolderModalVisible(false)
			await fetchRuleFolders()
			showToast('保存成功', 'success') 
		} catch (err) { 
			showToast('保存失败', 'error') 
		}
	}

	const deleteFolder = async (folderId: number) => {
		if (!confirm('确定删除该文件夹？规则将移至默认文件夹')) return
		
		try {
			const r = await authedFetch(`${apiBase}/api/rule-folders/${folderId}`, { method: 'DELETE' })
			if (r.ok) {
				await fetchRuleFolders()
				await fetchDetectionRules(searchRule, selectedFolderId)
				showToast('文件夹已删除', 'success')
			}
		} catch (err) {
			showToast('删除失败', 'error')
		}
	}

	useEffect(() => {
		if (!getStoredToken()) {
			router.replace('/login')
			return
		}

		const initData = async () => {
			await fetchRuleFolders()
			await fetchDetectionRules('', selectedFolderId)
			setLoading(false)
		}

		initData()
	}, [])

	useEffect(() => {
		if (apiBase) {
			fetchDetectionRules(searchRule, selectedFolderId)
		}
	}, [searchRule, selectedFolderId, apiBase])

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
								<div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-xl flex items-center justify-center">
									<Shield className="w-6 h-6 text-white" />
								</div>
								<h1 className="text-2xl font-bold text-gray-900">规则管理</h1>
							</div>
						</div>
						<div className="flex items-center space-x-2 text-sm text-gray-600">
							<Settings className="w-4 h-4" />
							<span>{detectionRules.length} 条规则</span>
						</div>
					</div>
				</div>
			</header>

			<div className="max-w-7xl mx-auto px-4 py-8">
				<div className="grid lg:grid-cols-4 gap-8">
					{/* Sidebar - Rule Folders */}
					<div className="lg:col-span-1">
						<div className="bg-white/70 backdrop-blur-xl rounded-2xl shadow-xl border border-white/50 overflow-hidden sticky top-24">
							<div className="p-4 border-b border-gray-100">
								<div className="flex items-center justify-between">
									<h3 className="font-bold text-gray-900 flex items-center">
										<Folder className="w-4 h-4 mr-2" />
										文件夹
									</h3>
									<button 
										onClick={() => { 
											setFolderForm({ id: null, name: '' })
											setFolderModalVisible(true) 
										}}
										className="w-8 h-8 bg-blue-100 hover:bg-blue-200 text-blue-600 rounded-lg flex items-center justify-center transition-colors duration-200"
									>
										<Plus className="w-4 h-4" />
									</button>
								</div>
							</div>
							
							<div className="max-h-80 overflow-auto">
								{ruleFolders.map((folder: any) => (
									<div 
										key={folder.id} 
										onClick={() => setSelectedFolderId(folder.id)}
										className={`p-3 cursor-pointer hover:bg-gray-50/50 transition-colors duration-200 ${
											selectedFolderId === folder.id ? 'bg-blue-50 border-r-2 border-blue-500' : ''
										}`}
									>
										<div className="flex items-center justify-between">
											<div className="flex items-center space-x-3">
												<Folder className={`w-4 h-4 ${selectedFolderId === folder.id ? 'text-blue-600' : 'text-gray-500'}`} />
												<span className={`font-medium ${selectedFolderId === folder.id ? 'text-blue-600' : 'text-gray-700'}`}>
													{folder.name}
												</span>
												<span className="text-xs text-gray-400 bg-gray-100 px-2 py-1 rounded">
													{folder.count || 0}
												</span>
											</div>
											{folder.id !== 1 && (
												<div className="flex space-x-1 opacity-0 group-hover:opacity-100 transition-opacity duration-200">
													<button
														onClick={(e) => { 
															e.stopPropagation()
															setFolderForm({ id: folder.id, name: folder.name })
															setFolderModalVisible(true) 
														}}
														className="w-6 h-6 bg-gray-100 hover:bg-gray-200 text-gray-600 rounded flex items-center justify-center text-xs"
													>
														<Edit className="w-3 h-3" />
													</button>
													<button
														onClick={(e) => { 
															e.stopPropagation()
															deleteFolder(folder.id)
														}}
														className="w-6 h-6 bg-red-100 hover:bg-red-200 text-red-600 rounded flex items-center justify-center text-xs"
													>
														<Trash2 className="w-3 h-3" />
													</button>
												</div>
											)}
										</div>
									</div>
								))}
							</div>
						</div>
					</div>

					{/* Main Content - Rules */}
					<div className="lg:col-span-3 space-y-6">
						{/* Search and Add */}
						<div className="bg-white/70 backdrop-blur-xl rounded-2xl shadow-xl border border-white/50 p-4">
							<div className="flex flex-col md:flex-row md:items-center md:justify-between space-y-4 md:space-y-0 md:space-x-4">
								<div className="relative flex-1">
									<Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
									<input
										value={searchRule}
										onChange={(e) => setSearchRule(e.target.value)}
										placeholder="搜索规则名称或描述..."
										className="w-full pl-10 pr-4 py-3 border border-gray-200 rounded-xl focus:ring-4 focus:ring-blue-500/10 focus:border-blue-500 transition-all duration-200"
									/>
								</div>
								<button
									onClick={openRuleAdd}
									className="px-6 py-3 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white font-medium rounded-xl shadow-lg hover:shadow-xl transition-all duration-200 flex items-center space-x-2"
								>
									<Plus className="w-5 h-5" />
									<span>新建规则</span>
								</button>
							</div>
						</div>

						{/* Rules List */}
						<div className="bg-white/70 backdrop-blur-xl rounded-2xl shadow-xl border border-white/50 overflow-hidden">
							<div className="overflow-auto" style={{ maxHeight: 'calc(100vh - 160px)', minHeight: '60vh' }}>
								{detectionRules.length > 0 ? (
									<div className="divide-y divide-gray-100">
										{detectionRules.map((rule: any) => (
											<div key={rule.id} className="p-4 hover:bg-gray-50/50 transition-colors duration-200 group">
												<div className="flex items-center justify-between">
													<div className="flex-1">
														<div className="flex items-center space-x-3 mb-2">
															<div className={`w-3 h-3 rounded-full ${rule.enabled ? 'bg-green-500' : 'bg-gray-400'}`}></div>
															<h4 className="font-semibold text-gray-900">{rule.name}</h4>
															<span className="text-xs text-gray-400">#{rule.id}</span>
														</div>
														<p className="text-gray-600 text-sm mb-2">{rule.description}</p>
														<div className="flex items-center space-x-4 text-xs text-gray-500">
															<span>组合：{rule.operator}</span>
															<span>模式：{(rule.patterns || []).length} 条</span>
															<span>类型：{rule.is_regex ? '正则' : '普通'}</span>
														</div>
													</div>
													<div className="flex items-center space-x-2">
														<button
															onClick={() => toggleRule(rule.id, rule.enabled)}
															className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors duration-200 flex items-center space-x-1 ${
																rule.enabled 
																	? 'bg-green-100 hover:bg-green-200 text-green-600' 
																	: 'bg-gray-100 hover:bg-gray-200 text-gray-600'
															}`}
														>
															<Power className="w-3 h-3" />
															<span>{rule.enabled ? '禁用' : '启用'}</span>
														</button>
														<button
															onClick={() => openRuleEdit(rule)}
															className="px-3 py-1.5 bg-blue-100 hover:bg-blue-200 text-blue-600 rounded-lg text-sm font-medium transition-colors duration-200 flex items-center space-x-1"
														>
															<Edit className="w-3 h-3" />
															<span>编辑</span>
														</button>
														<button
															onClick={() => deleteRule(rule.id)}
															className="px-3 py-1.5 bg-red-100 hover:bg-red-200 text-red-600 rounded-lg text-sm font-medium transition-colors duration-200 flex items-center space-x-1"
														>
															<Trash2 className="w-3 h-3" />
															<span>删除</span>
														</button>
													</div>
												</div>
											</div>
										))}
									</div>
								) : (
									<div className="p-12 text-center">
										<div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
											<Shield className="w-8 h-8 text-gray-400" />
										</div>
										<p className="text-gray-500 font-medium mb-2">暂无规则</p>
										<p className="text-gray-400 text-sm">创建第一个检测规则</p>
									</div>
								)}
							</div>
						</div>
					</div>
				</div>
			</div>

			{/* Rule Modal */}
			{ruleModalVisible && (
				<div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
					<div className="bg-white rounded-2xl shadow-2xl max-w-2xl w-full max-h-[90vh] overflow-auto">
						<div className="p-6 border-b border-gray-100">
							<h3 className="text-lg font-bold text-gray-900">
								{ruleModalMode === 'add' ? '新建规则' : '编辑规则'}
							</h3>
						</div>
						<div className="p-6 space-y-4">
							<div className="grid md:grid-cols-2 gap-4">
								<div className="space-y-2">
									<label className="block text-sm font-medium text-gray-700">规则名称*</label>
									<input
										value={ruleForm.name}
										onChange={(e) => setRuleForm({ ...ruleForm, name: e.target.value })}
										className="w-full px-3 py-2 border border-gray-200 rounded-lg focus:ring-4 focus:ring-blue-500/10 focus:border-blue-500 transition-all duration-200"
									/>
								</div>
								<div className="space-y-2">
									<label className="block text-sm font-medium text-gray-700">所属文件夹</label>
									<select
										value={ruleForm.folder_id}
										onChange={(e) => setRuleForm({ ...ruleForm, folder_id: Number(e.target.value) })}
										className="w-full px-3 py-2 border border-gray-200 rounded-lg focus:ring-4 focus:ring-blue-500/10 focus:border-blue-500 transition-all duration-200"
									>
										{ruleFolders.map((f: any) => (
											<option key={f.id} value={f.id}>{f.name}</option>
										))}
									</select>
								</div>
							</div>
							
							<div className="space-y-2">
								<label className="block text-sm font-medium text-gray-700">描述</label>
								<input
									value={ruleForm.description}
									onChange={(e) => setRuleForm({ ...ruleForm, description: e.target.value })}
									className="w-full px-3 py-2 border border-gray-200 rounded-lg focus:ring-4 focus:ring-blue-500/10 focus:border-blue-500 transition-all duration-200"
								/>
							</div>
							
							<div className="grid md:grid-cols-2 gap-4">
								<div className="space-y-2">
									<label className="block text-sm font-medium text-gray-700">组合逻辑</label>
									<select
										value={ruleForm.operator}
										onChange={(e) => setRuleForm({ ...ruleForm, operator: e.target.value })}
										className="w-full px-3 py-2 border border-gray-200 rounded-lg focus:ring-4 focus:ring-blue-500/10 focus:border-blue-500 transition-all duration-200"
									>
										<option value="OR">或 (任一匹配)</option>
										<option value="AND">与 (全部匹配)</option>
										<option value="NOT">非 (均不匹配)</option>
									</select>
								</div>
								<div className="space-y-2">
									<label className="block text-sm font-medium text-gray-700">匹配类型</label>
									<select
										value={ruleForm.is_regex ? '1' : '0'}
										onChange={(e) => setRuleForm({ ...ruleForm, is_regex: e.target.value === '1' })}
										className="w-full px-3 py-2 border border-gray-200 rounded-lg focus:ring-4 focus:ring-blue-500/10 focus:border-blue-500 transition-all duration-200"
									>
										<option value="1">正则表达式</option>
										<option value="0">普通包含</option>
									</select>
								</div>
							</div>
							
							<div className="space-y-2">
								<label className="block text-sm font-medium text-gray-700">匹配模式</label>
								<textarea
									value={ruleForm.patterns}
									onChange={(e) => setRuleForm({ ...ruleForm, patterns: e.target.value })}
									rows={4}
									placeholder="每行一个模式，或用逗号/分号分隔&#10;例如：ERROR|FATAL&#10;Out of memory"
									className="w-full px-3 py-2 border border-gray-200 rounded-lg focus:ring-4 focus:ring-blue-500/10 focus:border-blue-500 transition-all duration-200 resize-none font-mono text-sm"
								/>
							</div>
							
							<div className="flex items-center">
								<input
									type="checkbox"
									checked={!!ruleForm.enabled}
									onChange={(e) => setRuleForm({ ...ruleForm, enabled: e.target.checked })}
									className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
								/>
								<label className="ml-2 text-sm font-medium text-gray-700">启用该规则</label>
							</div>
						</div>
						<div className="p-6 border-t border-gray-100 flex justify-end space-x-3">
							<button
								onClick={() => setRuleModalVisible(false)}
								className="px-4 py-2 text-gray-600 hover:text-gray-800 hover:bg-gray-100 rounded-lg transition-colors duration-200"
							>
								取消
							</button>
							<button
								onClick={submitRule}
								disabled={!ruleForm.name || !ruleForm.patterns}
								className="px-6 py-2 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 disabled:from-gray-400 disabled:to-gray-500 text-white font-medium rounded-lg shadow-lg hover:shadow-xl disabled:shadow-none transition-all duration-200 disabled:cursor-not-allowed"
							>
								保存
							</button>
						</div>
					</div>
				</div>
			)}

			{/* Folder Modal */}
			{folderModalVisible && (
				<div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
					<div className="bg-white rounded-2xl shadow-2xl max-w-md w-full">
						<div className="p-6 border-b border-gray-100">
							<h3 className="text-lg font-bold text-gray-900">
								{folderForm.id ? '重命名文件夹' : '新建文件夹'}
							</h3>
						</div>
						<div className="p-6 space-y-4">
							<div className="space-y-2">
								<label className="block text-sm font-medium text-gray-700">文件夹名称</label>
								<input
									value={folderForm.name}
									onChange={(e) => setFolderForm({ ...folderForm, name: e.target.value })}
									className="w-full px-3 py-2 border border-gray-200 rounded-lg focus:ring-4 focus:ring-blue-500/10 focus:border-blue-500 transition-all duration-200"
								/>
							</div>
						</div>
						<div className="p-6 border-t border-gray-100 flex justify-end space-x-3">
							<button
								onClick={() => setFolderModalVisible(false)}
								className="px-4 py-2 text-gray-600 hover:text-gray-800 hover:bg-gray-100 rounded-lg transition-colors duration-200"
							>
								取消
							</button>
							<button
								onClick={submitFolder}
								disabled={!folderForm.name}
								className="px-6 py-2 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 disabled:from-gray-400 disabled:to-gray-500 text-white font-medium rounded-lg shadow-lg hover:shadow-xl disabled:shadow-none transition-all duration-200 disabled:cursor-not-allowed"
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