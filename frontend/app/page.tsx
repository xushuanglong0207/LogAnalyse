// @ts-nocheck
'use client'

import { useState, useEffect, useRef, useMemo } from 'react'

// 动态计算 API 基址
function computeApiBase(): string {
	if (typeof window !== 'undefined') {
		const protocol = window.location.protocol
		const host = window.location.hostname
		return `${protocol}//${host}:8001`
	}
	return ''
}

// 简易Modal组件（美化）
function Modal({ visible, title, children, onClose, footer }: any) {
	if (!visible) return null
	return (
		<div style={{ position: 'fixed', inset: 0, background: 'rgba(15, 23, 42, 0.45)', backdropFilter: 'blur(6px)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 50 }} onClick={onClose}>
			<div className="ui-card" onClick={(e) => e.stopPropagation()} style={{ width: 'min(920px, 94vw)', maxHeight: '86vh', overflow: 'auto' }}>
				<div className="modal-header">
					<h3 className="modal-title">{title}</h3>
					<button className="btn btn-outline" onClick={onClose}>×</button>
				</div>
				<div className="modal-body">{children}</div>
				{footer && <div className="modal-footer">{footer}</div>}
			</div>
		</div>
	)
}

function Toasts({ toasts, remove }: any) {
	return (
		<div style={{ position: 'fixed', top: 16, right: 16, display: 'flex', flexDirection: 'column', gap: 8, zIndex: 70 }}>
			{toasts.map((t: any) => (
				<div key={t.id} style={{ minWidth: 260, maxWidth: 420, padding: '10px 14px', borderRadius: 10, color: t.type === 'error' ? '#991b1b' : t.type === 'success' ? '#065f46' : '#1f2937', background: t.type === 'error' ? '#fee2e2' : t.type === 'success' ? '#d1fae5' : '#e5e7eb', boxShadow: '0 10px 30px rgba(2,6,23,0.12)' }} onClick={() => remove(t.id)}>
					<div style={{ fontWeight: 700, marginBottom: 2 }}>{t.type === 'error' ? '错误' : t.type === 'success' ? '成功' : '提示'}</div>
					<div style={{ whiteSpace: 'pre-wrap' }}>{t.message}</div>
				</div>
			))}
		</div>
	)
}

function ConfirmModal({ visible, text, onConfirm, onCancel }: any) {
	if (!visible) return null
	return (
		<Modal visible={visible} title="确认操作" onClose={onCancel} footer={[
			<button key="cancel" onClick={onCancel} style={{ background: '#fff', border: '1px solid #e5e7eb', padding: '8px 14px', borderRadius: 8, cursor: 'pointer' }}>取消</button>,
			<button key="ok" onClick={onConfirm} style={{ background: '#ef4444', color: '#fff', padding: '8px 14px', borderRadius: 8, border: 'none', cursor: 'pointer' }}>确定</button>
		]}>
			<div style={{ color: '#374151' }}>{text}</div>
		</Modal>
	)
}

export default function Home() {
	const [apiBase, setApiBase] = useState('')
	const getApiBase = () => apiBase || computeApiBase()

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

	const [currentUser, setCurrentUser] = useState<any>(null)
	const [currentPage, setCurrentPage] = useState('dashboard')
	const [uploadedFiles, setUploadedFiles] = useState<any[]>([])
	const [dashboardStats, setDashboardStats] = useState<any>({ uploaded_files: 0, detected_issues: 0, detection_rules: 7, recent_activity: [] })
	const [detectionRules, setDetectionRules] = useState<any[]>([])
	const [ruleFolders, setRuleFolders] = useState<any[]>([])
	const [selectedFolderId, setSelectedFolderId] = useState<number | null>(null)
	const [searchRule, setSearchRule] = useState('')
	const [draggingRuleId, setDraggingRuleId] = useState<number | null>(null)
	const [backendStatus, setBackendStatus] = useState<'connected' | 'connecting' | 'failed'>('connecting')
	const [analysisResults, setAnalysisResults] = useState<any[]>([])
	const [users, setUsers] = useState<any[]>([])

	// —— 问题库：状态 ——
	const [problems, setProblems] = useState<any[]>([])
	const [problemModalVisible, setProblemModalVisible] = useState(false)
	const [problemForm, setProblemForm] = useState<any>({ id: null, title: '', url: '', error_type: '' })
	const [problemFilterType, setProblemFilterType] = useState<string>('')
	const [problemFilterQuery, setProblemFilterQuery] = useState<string>('')
	const [problemFilterCategory, setProblemFilterCategory] = useState<string>('')
	const [problemStatsByType, setProblemStatsByType] = useState<Record<string, number>>({})

	// Toast 通知状态
	const [toasts, setToasts] = useState<any[]>([])
	const showToast = (message: string, type: 'success' | 'error' | 'info' = 'info') => {
		const id = Date.now()
		setToasts(prev => [...prev, { id, message, type }])
		setTimeout(() => removeToast(id), 5000)
	}
	const removeToast = (id: number) => setToasts(prev => prev.filter(t => t.id !== id))

	// 确认弹窗状态
	const [confirmState, setConfirmState] = useState<{ visible: boolean; text: string; resolve: null | ((v: boolean) => void) }>({ visible: false, text: '', resolve: null })
	const openConfirm = (text: string) => new Promise<boolean>((resolve) => { setConfirmState({ visible: true, text, resolve }) })

	// 预览弹窗
	const [pasteText, setPasteText] = useState('')
	const [previewVisible, setPreviewVisible] = useState(false)
	const [previewTitle, setPreviewTitle] = useState('')
	const [previewContent, setPreviewContent] = useState('')
	const [previewMode, setPreviewMode] = useState<'shell' | 'txt'>('shell')
	const [previewSearch, setPreviewSearch] = useState('')
	const previewContainerRef = useRef<HTMLDivElement | null>(null)
	const [currentMatchIndex, setCurrentMatchIndex] = useState(0)
	const previewMatches = useMemo(() => {
		if (!previewSearch) return 0
		try { const re = new RegExp(previewSearch.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'ig'); return (previewContent.match(re) || []).length } catch { return 0 }
	}, [previewSearch, previewContent])
	useEffect(() => { setCurrentMatchIndex(0) }, [previewSearch, previewVisible])
	const jumpMatch = (delta: number) => {
		const cont = previewContainerRef.current
		if (!cont) return
		const marks = Array.from(cont.querySelectorAll('mark'))
		if (marks.length === 0) return
		const next = (currentMatchIndex + delta + marks.length) % marks.length
		setCurrentMatchIndex(next)
		marks.forEach(m => m.removeAttribute('data-active'))
		const target = marks[next] as HTMLElement
		target.setAttribute('data-active', '1')
		target.scrollIntoView({ block: 'center' })
	}

	// 分析详情弹窗
	const [detailVisible, setDetailVisible] = useState(false)
	const [detailData, setDetailData] = useState<any>(null)
	const [collapsedGroups, setCollapsedGroups] = useState<Record<string, boolean>>({})
	useEffect(() => { if (detailVisible) setCollapsedGroups({}) }, [detailVisible])
	useEffect(() => {
		if (!detailVisible || !detailData?.data?.issues) return
		const types = Array.from(new Set((detailData.data.issues || []).map((it: any) => String(it.matched_text || it.rule_name || '其他'))))
		fetchProblemStats(types)
	}, [detailVisible, detailData])

	// 用户/规则弹窗
	const [userModalVisible, setUserModalVisible] = useState(false)
	const [userModalMode, setUserModalMode] = useState<'add' | 'edit'>('add')
	const [userForm, setUserForm] = useState<any>({ id: null, username: '', email: '', password: '', role: '普通用户' })
	const [ruleModalVisible, setRuleModalVisible] = useState(false)
	const [ruleModalMode, setRuleModalMode] = useState<'add' | 'edit'>('add')
	const [ruleForm, setRuleForm] = useState<any>({ id: null, name: '', description: '', enabled: true, patterns: '', operator: 'OR', is_regex: true, folder_id: 1 })
	const [folderModalVisible, setFolderModalVisible] = useState(false)
	const [folderForm, setFolderForm] = useState<any>({ id: null, name: '' })

	// 个人中心
	const [profileVisible, setProfileVisible] = useState(false)
	const [pwdForm, setPwdForm] = useState({ old_password: '', new_password: '' })

	// 状态卡
	const [cardExpanded, setCardExpanded] = useState(true)
	useEffect(() => {
		const timer = setTimeout(() => setCardExpanded(false), 10000)
		return () => clearTimeout(timer)
	}, [])

	const checkBackendStatus = async (base?: string) => {
		const urlBase = base || getApiBase()
		if (!urlBase) return false
		try { const response = await fetch(`${urlBase}/health`); if (response.ok) { setBackendStatus('connected'); return true } else { setBackendStatus('failed'); return false } } catch { setBackendStatus('failed'); return false }
	}
	const fetchDashboardStats = async () => { try { const r = await authedFetch(`${getApiBase()}/api/dashboard/stats`); if (r.ok) setDashboardStats(await r.json()) } catch {} }
	const fetchUploadedFiles = async () => { try { const r = await authedFetch(`${getApiBase()}/api/logs`); if (r.ok) { const d = await r.json(); setUploadedFiles(d.files || []) } } catch {} }
	const fetchDetectionRules = async (q = '', folderId: number | null = null) => { try { const params = new URLSearchParams(); if (q) params.set('query', q); if (folderId !== null) params.set('folder_id', String(folderId)); const r = await authedFetch(`${getApiBase()}/api/rules?${params.toString()}`); if (r.ok) { const d = await r.json(); setDetectionRules(d.rules || []) } } catch {} }
	const fetchRuleFolders = async () => { try { const r = await authedFetch(`${getApiBase()}/api/rule-folders`); if (r.ok) { const d = await r.json(); setRuleFolders(d.folders || []); if (d.folders && d.folders.length && selectedFolderId === null) setSelectedFolderId(d.folders[0].id) } } catch {} }
	const fetchUsers = async () => { try { const r = await authedFetch(`${getApiBase()}/api/users`); if (r.ok) { const d = await r.json(); setUsers(d.users || []) } } catch {} }
	const fetchMe = async () => { try { const r = await authedFetch(`${getApiBase()}/api/auth/me`); if (r.ok) { const d = await r.json(); setCurrentUser(d.user) } } catch {} }
	const fetchAnalysisResults = async () => { try { const r = await authedFetch(`${getApiBase()}/api/analysis/results`); if (r.ok) { const d = await r.json(); setAnalysisResults(d.results || []) } } catch {} }

	useEffect(() => {
		const base = computeApiBase(); setApiBase(base)
		;(async () => { const ok = await checkBackendStatus(base); if (ok) { await fetchMe(); await Promise.all([fetchDashboardStats(), fetchUploadedFiles(), fetchRuleFolders(), fetchDetectionRules('', selectedFolderId), fetchUsers(), fetchAnalysisResults()]) } })()
	}, [])
	useEffect(() => { if (apiBase && currentUser) fetchDetectionRules(searchRule, selectedFolderId) }, [searchRule, selectedFolderId, apiBase, currentUser])

	// —— 交互与业务辅助 ——
	const askConfirm = (text: string) => openConfirm(text)
	const parsePatterns = (s: string) => (s || '').split(/\r?\n|,|;|、/).map(v => v.trim()).filter(Boolean)

	// 预览高亮渲染
	const renderHighlighted = (text: string, q: string) => {
		if (!q) return (<pre style={{ margin: 0, whiteSpace: 'pre-wrap' }}>{text}</pre>)
		try {
			const re = new RegExp(q.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'gi')
			const html = text.replace(re, (m) => `<mark style="background:#fde68a">${m}</mark>`)
			return (<pre style={{ margin: 0, whiteSpace: 'pre-wrap' }} dangerouslySetInnerHTML={{ __html: html }} />)
		} catch {
			return (<pre style={{ margin: 0, whiteSpace: 'pre-wrap' }}>{text}</pre>)
		}
	}

	// —— 日志：上传/分析/预览/删除 ——
	const handleFileUpload = async (e: any) => {
		try {
			const files = Array.from(e.target.files || [])
			for (const f of files as any[]) {
				const fd = new FormData()
				fd.append('file', f)
				const r = await authedFetch(`${getApiBase()}/api/logs/upload`, { method: 'POST', body: fd })
				if (!r.ok) throw new Error('上传失败')
			}
			await Promise.all([fetchUploadedFiles(), fetchDashboardStats()])
			showToast('文件上传成功', 'success')
		} catch {
			showToast('文件上传失败', 'error')
		} finally {
			try { e.target.value = '' } catch {}
		}
	}
	const handleAnalyzeText = async () => {
		try {
			if (!pasteText) return showToast('请先粘贴内容', 'info')
			const r = await authedFetch(`${getApiBase()}/api/logs/analyze_text`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ text: pasteText, filename: 'pasted.log' }) })
			if (r.ok) {
				const d = await r.json(); setAnalysisResults(prev => [...prev.filter(x => x.file_id !== d.file_id), d]); await Promise.all([fetchUploadedFiles(), fetchDashboardStats()]); setPasteText(''); showToast('分析完成', 'success')
			} else {
				showToast('分析失败', 'error')
			}
		} catch { showToast('分析失败', 'error') }
	}
	const analyzeFile = async (fileId: number) => {
		try { const r = await authedFetch(`${getApiBase()}/api/logs/${fileId}/analyze`, { method: 'POST' }); if (r.ok) { const d = await r.json(); setAnalysisResults(prev => [...prev.filter(x => x.file_id !== d.file_id), d]); await fetchDashboardStats(); showToast('分析完成', 'success') } else showToast('分析失败', 'error') } catch { showToast('分析失败', 'error') }
	}
	const deleteFile = async (fileId: number) => {
		const ok = await askConfirm('确定删除该日志文件？')
		if (!ok) return
		try { const r = await authedFetch(`${getApiBase()}/api/logs/${fileId}`, { method: 'DELETE' }); if (r.ok) { await Promise.all([fetchUploadedFiles(), fetchDashboardStats()]); setAnalysisResults(prev => prev.filter(x => x.file_id !== fileId)); showToast('删除成功', 'success') } else showToast('删除失败', 'error') } catch { showToast('删除失败', 'error') }
	}
	const openFilePreview = async (fileId: number, filename: string) => {
		try { const r = await authedFetch(`${getApiBase()}/api/logs/${fileId}`); if (r.ok) { const d = await r.json(); setPreviewTitle(`${d.filename}`); setPreviewContent(d.content || ''); setPreviewMode('shell'); setPreviewVisible(true) } } catch {}
	}
	const openAnalysisDetail = async (fileId: number, filename: string) => {
		try { const r = await authedFetch(`${getApiBase()}/api/analysis/${fileId}`); if (r.ok) { const d = await r.json(); setDetailData({ title: `${filename}`, data: d }); setDetailVisible(true) } } catch { showToast('详情加载失败', 'error') }
	}

	// —— 规则：增删改查/拖拽 ——
	const openRuleAdd = () => { setRuleForm({ id: null, name: '', description: '', enabled: true, patterns: '', operator: 'OR', is_regex: true, folder_id: ruleFolders[0]?.id || 1 }); setRuleModalMode('add'); setRuleModalVisible(true) }
	const openRuleEdit = (rule: any) => { setRuleForm({ id: rule.id, name: rule.name, description: rule.description || '', enabled: !!rule.enabled, patterns: (rule.patterns || []).join('\n'), operator: rule.operator || 'OR', is_regex: !!rule.is_regex, folder_id: rule.folder_id || 1 }); setRuleModalMode('edit'); setRuleModalVisible(true) }
	const submitRule = async () => {
		try {
			const payload = { name: ruleForm.name, description: ruleForm.description || '', enabled: !!ruleForm.enabled, patterns: parsePatterns(ruleForm.patterns), operator: (ruleForm.operator || 'OR'), is_regex: !!ruleForm.is_regex, folder_id: ruleForm.folder_id || 1 }
			let r
			if (ruleModalMode === 'add') r = await authedFetch(`${getApiBase()}/api/rules`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) })
			else r = await authedFetch(`${getApiBase()}/api/rules/${ruleForm.id}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) })
			if (r.ok) { setRuleModalVisible(false); await fetchDetectionRules(searchRule, selectedFolderId); await fetchRuleFolders(); showToast('保存成功', 'success') } else showToast('保存失败', 'error')
		} catch { showToast('保存失败', 'error') }
	}
	const deleteRule = async (ruleId: number) => { const ok = await askConfirm('确定删除该规则？'); if (!ok) return; try { const r = await authedFetch(`${getApiBase()}/api/rules/${ruleId}`, { method: 'DELETE' }); if (r.ok) { await fetchDetectionRules(searchRule, selectedFolderId); await fetchRuleFolders(); showToast('删除成功', 'success') } else showToast('删除失败', 'error') } catch { showToast('删除失败', 'error') } }
	const toggleRule = async (ruleId: number, enabled: boolean) => { try { const r = await authedFetch(`${getApiBase()}/api/rules/${ruleId}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ enabled: !enabled }) }); if (r.ok) { await fetchDetectionRules(searchRule, selectedFolderId); showToast(!enabled ? '已启用' : '已禁用', 'success') } } catch {} }
	const onDragStartRule = (id: number) => setDraggingRuleId(id)
	const onDropToFolder = async (folderId: number) => { if (!draggingRuleId) return; try { const r = await authedFetch(`${getApiBase()}/api/rules/${draggingRuleId}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ folder_id: folderId }) }); if (r.ok) { await fetchDetectionRules(searchRule, selectedFolderId); await fetchRuleFolders(); setDraggingRuleId(null); showToast('已移动到文件夹', 'success') } } catch { setDraggingRuleId(null) } }

	// —— 用户：增删改 ——
	const openUserAdd = () => { setUserForm({ id: null, username: '', email: '', password: '', role: '普通用户' }); setUserModalMode('add'); setUserModalVisible(true) }
	const openUserEdit = (user: any) => { setUserForm({ id: user.id, username: user.username, email: user.email || '', password: '', role: user.role || '普通用户' }); setUserModalMode('edit'); setUserModalVisible(true) }
	const submitUser = async () => {
		try {
			if (userModalMode === 'add') {
				const r = await authedFetch(`${getApiBase()}/api/users`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ username: userForm.username, email: userForm.email, role: userForm.role, password: userForm.password }) })
				if (!r.ok) throw new Error('创建失败')
			} else {
				const r = await authedFetch(`${getApiBase()}/api/users/${userForm.id}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ email: userForm.email, role: userForm.role, password: userForm.password }) })
				if (!r.ok) throw new Error('更新失败')
			}
			setUserModalVisible(false); await fetchUsers(); showToast('已保存', 'success')
		} catch { showToast('保存失败', 'error') }
	}
	const confirmDeleteUser = async (id: number) => { const ok = await askConfirm('确定删除该用户？'); if (!ok) return; try { const r = await authedFetch(`${getApiBase()}/api/users/${id}`, { method: 'DELETE' }); if (r.ok) { await fetchUsers(); showToast('已删除', 'success') } else showToast('删除失败', 'error') } catch { showToast('删除失败', 'error') } }

	// 顶部导航
	const Nav = () => (
		<nav className="ui-card" style={{ position: 'sticky', top: 0, zIndex: 40, margin: '0 0 16px', padding: '12px 24px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
			<h1 style={{ fontSize: '1.25rem', fontWeight: 800, margin: 0 }}>🚀 日志分析平台</h1>
			<div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
				{[
					{ id: 'dashboard', label: '📊 仪表板' },
					{ id: 'logs', label: '📁 日志管理' },
					{ id: 'rules', label: '🔍 规则管理' },
					{ id: 'problems', label: '📚 问题库' },
					{ id: 'users', label: '👥 用户管理' }
				].map(nav => (
					<button key={nav.id} onClick={() => setCurrentPage(nav.id)} className="btn" style={{ background: currentPage === nav.id ? 'linear-gradient(135deg, var(--brand), var(--brand2))' : '#fff', color: currentPage === nav.id ? '#fff' : '#374151' }}>{nav.label}</button>
				))}
				<button onClick={() => setProfileVisible(true)} className="btn btn-outline">个人中心</button>
			</div>
		</nav>
	)

	// 个人中心弹窗
	const ProfileModal = () => (
		<Modal visible={profileVisible} title="个人中心" onClose={() => setProfileVisible(false)} footer={[
							<button key="logout" className="btn btn-danger" onClick={() => { localStorage.removeItem('token'); sessionStorage.removeItem('token'); window.location.href = '/login' }}>退出登录</button>,
				<button key="ok" className="btn btn-primary" onClick={async () => { try { await authedFetch(`${getApiBase()}/api/users/${currentUser?.id}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ position: currentUser?.position||'' }) }); const r = await authedFetch(`${getApiBase()}/api/auth/change_password`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(pwdForm) }); if (r.ok) { showToast('资料已更新，请重新登录', 'success'); window.location.href = '/login' } else showToast('已保存职位，密码未修改', 'info') } catch { showToast('更新失败', 'error') } }}>保存资料</button>
		]}>
			<div className="stack-16">
									<div style={{ color: '#374151' }}>当前用户：<b>{currentUser?.username}</b></div>
					<div className="form-grid">
						<div className="form-col">
							<div className="label">职位</div>
							<input className="ui-input" value={currentUser?.position||''} onChange={(e) => setCurrentUser({ ...currentUser, position: e.target.value })} placeholder="如：运维工程师" />
						</div>
						<div className="form-col">
							<div className="label">原密码</div>
							<input className="ui-input" type="password" value={pwdForm.old_password} onChange={(e) => setPwdForm({ ...pwdForm, old_password: e.target.value })} />
						</div>
						<div className="form-col">
							<div className="label">新密码</div>
							<input className="ui-input" type="password" value={pwdForm.new_password} onChange={(e) => setPwdForm({ ...pwdForm, new_password: e.target.value })} />
						</div>
					</div>
			</div>
		</Modal>
	)

	// 示例：用户编辑弹窗（美化）
	const UserModal = () => (
		<Modal visible={userModalVisible} title={userModalMode === 'add' ? '添加用户' : '编辑用户'} onClose={() => setUserModalVisible(false)} footer={[
			<button key="cancel" className="btn btn-outline" onClick={() => setUserModalVisible(false)}>取消</button>,
			<button key="ok" className="btn btn-primary" onClick={() => {/* 提交用户表单逻辑 */}}>提交</button>
		]}>
			<div className="form-grid">
				<div className="form-col">
					<div className="label">用户名*</div>
					<input className="ui-input" value={userForm.username} onChange={(e) => setUserForm({ ...userForm, username: e.target.value })} />
				</div>
				<div className="form-col">
					<div className="label">邮箱(选填)</div>
					<input className="ui-input" value={userForm.email} onChange={(e) => setUserForm({ ...userForm, email: e.target.value })} />
				</div>
				<div className="form-col">
					<div className="label">角色*</div>
					<select className="ui-select" value={userForm.role} onChange={(e) => setUserForm({ ...userForm, role: e.target.value })}>
						<option value="管理员">管理员</option>
						<option value="普通用户">普通用户</option>
					</select>
				</div>
				{userModalMode === 'add' && (
					<div className="form-col">
						<div className="label">密码*</div>
						<input className="ui-input" type="password" value={userForm.password} onChange={(e) => setUserForm({ ...userForm, password: e.target.value })} />
					</div>
				)}
			</div>
		</Modal>
	)

	// 示例：规则弹窗（美化）
	const RuleModal = () => (
		<Modal visible={ruleModalVisible} title={ruleModalMode === 'add' ? '新建规则' : '编辑规则'} onClose={() => setRuleModalVisible(false)} footer={[
			<button key="cancel" className="btn btn-outline" onClick={() => setRuleModalVisible(false)}>取消</button>,
			<button key="ok" className="btn btn-primary" onClick={() => {/* 提交规则表单 */}}>保存</button>
		]}>
			<div className="form-grid">
				<div className="form-col">
					<div className="label">规则名称*</div>
					<input className="ui-input" value={ruleForm.name} onChange={(e) => setRuleForm({ ...ruleForm, name: e.target.value })} />
				</div>
				<div className="form-col">
					<div className="label">所属文件夹</div>
					<select className="ui-select" value={ruleForm.folder_id} onChange={(e) => setRuleForm({ ...ruleForm, folder_id: Number(e.target.value) })}>
						{ruleFolders.map((f: any) => <option key={f.id} value={f.id}>{f.name}</option>)}
					</select>
				</div>
				<div className="form-col" style={{ gridColumn: '1 / -1' }}>
					<div className="label">描述</div>
					<input className="ui-input" value={ruleForm.description} onChange={(e) => setRuleForm({ ...ruleForm, description: e.target.value })} />
				</div>
				<div className="form-col">
					<div className="label">组合</div>
					<select className="ui-select" value={ruleForm.operator} onChange={(e) => setRuleForm({ ...ruleForm, operator: e.target.value })}>
						<option value="OR">或 (任一匹配)</option>
						<option value="AND">与 (全部匹配)</option>
						<option value="NOT">非 (均不匹配)</option>
					</select>
				</div>
				<div className="form-col">
					<div className="label">是否正则</div>
					<select className="ui-select" value={ruleForm.is_regex ? '1' : '0'} onChange={(e) => setRuleForm({ ...ruleForm, is_regex: e.target.value === '1' })}>
						<option value="1">正则</option>
						<option value="0">普通包含</option>
					</select>
				</div>
				<div className="form-col" style={{ gridColumn: '1 / -1' }}>
					<div className="label">匹配模式</div>
					<textarea className="ui-input" style={{ minHeight: 120 }} value={ruleForm.patterns} onChange={(e) => setRuleForm({ ...ruleForm, patterns: e.target.value })} placeholder="正则匹配可写多个：OOM|Out of memory；组合选择 与/或/非 决定多模式关系" />
				</div>
				<div className="form-col">
					<label style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
						<input type="checkbox" checked={!!ruleForm.enabled} onChange={(e) => setRuleForm({ ...ruleForm, enabled: e.target.checked })} /> 启用该规则
					</label>
				</div>
			</div>
		</Modal>
	)

	// 文件夹弹窗
	const FolderModal = () => (
		<Modal visible={folderModalVisible} title={folderForm.id ? '重命名文件夹' : '新建文件夹'} onClose={() => setFolderModalVisible(false)} footer={[
			<button key="cancel" className="btn btn-outline" onClick={() => setFolderModalVisible(false)}>取消</button>,
			<button key="ok" className="btn btn-primary" onClick={async () => { try { if (folderForm.id) { await authedFetch(`${getApiBase()}/api/rule-folders/${folderForm.id}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name: folderForm.name }) }) } else { await authedFetch(`${getApiBase()}/api/rule-folders`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name: folderForm.name }) }) } setFolderModalVisible(false); await fetchRuleFolders(); showToast('保存成功', 'success') } catch { showToast('保存失败', 'error') } }}>保存</button>
		]}>
			<div className="form-grid">
				<div className="form-col">
					<div className="label">文件夹名称</div>
					<input className="ui-input" value={folderForm.name} onChange={(e) => setFolderForm({ ...folderForm, name: e.target.value })} />
				</div>
			</div>
		</Modal>
	)

	// 日志管理页面
	const LogManagement = () => (
		<div style={{ padding: '2rem' }}>
			<h2 style={{ fontSize: '1.5rem', fontWeight: 'bold', marginBottom: '1rem' }}>📁 日志管理</h2>
			<div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: 16, marginBottom: 24 }}>
				<div style={{ background: 'rgba(255,255,255,0.75)', backdropFilter: 'blur(6px)', border: '1px solid rgba(255,255,255,0.35)', borderRadius: 12, padding: 16 }}>
					<h3 style={{ fontWeight: 600, marginBottom: 12 }}>上传日志文件（支持任意扩展名）</h3>
					<div style={{ border: '2px dashed #d1d5db', borderRadius: 8, padding: 24, textAlign: 'center' }}>
						<input type="file" multiple onChange={handleFileUpload} style={{ display: 'none' }} id="fileUpload" />
						<label htmlFor="fileUpload" style={{ cursor: 'pointer', color: '#2563eb', fontWeight: 600 }}>📎 点击选择文件或拖拽到此处</label>
					</div>
				</div>
				<div style={{ background: 'rgba(255,255,255,0.75)', backdropFilter: 'blur(6px)', border: '1px solid rgba(255,255,255,0.35)', borderRadius: 12, padding: 16 }}>
					<h3 style={{ fontWeight: 600, marginBottom: 8 }}>直接粘贴文本分析（≤ 5MB）</h3>
					<textarea value={pasteText} onChange={(e) => setPasteText(e.target.value)} placeholder="在此粘贴日志文本..." style={{ width: '100%', minHeight: 160, border: '1px solid #e5e7eb', borderRadius: 8, padding: 12, fontFamily: "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace" }} />
					<div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 8 }}>
						<span style={{ color: '#6b7280', fontSize: 12 }}>当前大小：{(new Blob([pasteText]).size / 1024).toFixed(2)} KB</span>
						<button onClick={handleAnalyzeText} style={{ background: '#2563eb', color: 'white', padding: '8px 14px', borderRadius: 8, border: 'none', cursor: 'pointer' }}>分析文本</button>
					</div>
				</div>
			</div>

			{uploadedFiles.length > 0 && (
				<div style={{ background: 'rgba(255,255,255,0.75)', backdropFilter: 'blur(6px)', border: '1px solid rgba(255,255,255,0.35)', borderRadius: 12, padding: 16, maxHeight: 360, overflow: 'auto' }}>
					<h3 style={{ fontWeight: 600, marginBottom: 12 }}>已上传文件 ({uploadedFiles.length})</h3>
					{uploadedFiles.map((file: any) => (
						<div key={file.id} onDoubleClick={() => openFilePreview(file.id, file.filename)} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: 12, border: '1px solid #e5e7eb', borderRadius: 8, marginBottom: 8, cursor: 'zoom-in' }}>
							<div>
								<p style={{ fontWeight: 600, margin: 0 }}>{file.filename}</p>
								<p style={{ color: '#6b7280', fontSize: 12, margin: 0 }}>{(file.size / 1024).toFixed(2)} KB - {new Date(file.upload_time).toLocaleString()}</p>
							</div>
							<div style={{ display: 'flex', gap: 8 }}>
								<button onClick={() => analyzeFile(file.id)} style={{ background: '#2563eb', color: 'white', padding: '6px 10px', borderRadius: 6, border: 'none', cursor: 'pointer' }}>分析</button>
								<button onClick={() => deleteFile(file.id)} style={{ background: '#ef4444', color: 'white', padding: '6px 10px', borderRadius: 6, border: 'none', cursor: 'pointer' }}>删除</button>
							</div>
						</div>
					))}
				</div>
			)}

			<Modal visible={previewVisible} title={previewTitle} onClose={() => setPreviewVisible(false)}>
				<div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8, gap: 8 }}>
					<div style={{ display: 'flex', gap: 8 }}>
						<button onClick={() => setPreviewMode('shell')} style={{ padding: '6px 10px', borderRadius: 6, border: '1px solid #e5e7eb', background: previewMode === 'shell' ? '#111827' : '#fff', color: previewMode === 'shell' ? '#d1fae5' : '#111' }}>Shell</button>
						<button onClick={() => setPreviewMode('txt')} style={{ padding: '6px 10px', borderRadius: 6, border: '1px solid #e5e7eb', background: previewMode === 'txt' ? '#111827' : '#fff', color: previewMode === 'txt' ? '#d1fae5' : '#111' }}>TXT</button>
					</div>
					<div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
						<input placeholder="搜索 (回车下一个，Shift+回车上一个)" value={previewSearch} onChange={(e) => setPreviewSearch(e.target.value)} onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); jumpMatch(e.shiftKey ? -1 : 1) } }} style={{ border: '1px solid #e5e7eb', borderRadius: 8, padding: '6px 10px', fontFamily: 'ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Noto Sans, Ubuntu, Cantarell, Helvetica Neue, Arial' }} />
						<span style={{ color: '#6b7280', fontSize: 12, fontFamily: 'ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Noto Sans, Ubuntu, Cantarell, Helvetica Neue, Arial' }}>匹配: {previewMatches}{previewMatches>0?`（第 ${currentMatchIndex+1} / ${previewMatches} 个）`:''}</span>
						<button onClick={() => setPreviewSearch('')} style={{ border: '1px solid #e5e7eb', background: '#fff', padding: '4px 8px', borderRadius: 6, cursor: 'pointer' }}>清空</button>
					</div>
				</div>
				<div ref={previewContainerRef} style={{ maxHeight: '65vh', overflow: 'auto', borderRadius: 8, border: '1px solid #e5e7eb' }}>
					{previewMode === 'shell' ? (
						<div style={{ background: '#0b1220', color: '#d1fae5', padding: 12, fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace', fontSize: 12, lineHeight: 1.5 }}>
							{renderHighlighted(previewContent, previewSearch)}
						</div>
					) : (
						<div style={{ background: '#fff', color: '#111827', padding: 12 }}>
							{renderHighlighted(previewContent, previewSearch)}
						</div>
					)}
				</div>
			</Modal>
		</div>
	)

	// 规则管理页面
	const RuleManagement = () => (
		<div style={{ padding: '2rem' }}>
			<h2 style={{ fontSize: '1.5rem', fontWeight: 'bold', marginBottom: '1rem' }}>🔍 规则管理</h2>
			<div style={{ display: 'grid', gridTemplateColumns: '260px 1fr', gap: 16 }}>
				<div style={{ background: 'rgba(255,255,255,0.75)', backdropFilter: 'blur(6px)', border: '1px solid rgba(255,255,255,0.35)', borderRadius: 12, padding: 12, maxHeight: 520, overflow: 'auto' }}>
					<div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
						<h4 style={{ margin: 0 }}>规则文件夹</h4>
						<button onClick={() => { setFolderForm({ id: null, name: '' }); setFolderModalVisible(true) }} style={{ border: 'none', background: '#2563eb', color: '#fff', padding: '6px 10px', borderRadius: 6, cursor: 'pointer' }}>+ 文件夹</button>
					</div>
					{ruleFolders.map((f: any) => (
						<div key={f.id} onClick={() => setSelectedFolderId(f.id)} onDragOver={(e) => e.preventDefault()} onDrop={() => onDropToFolder(f.id)} style={{ padding: 10, borderRadius: 8, cursor: 'pointer', background: selectedFolderId === f.id ? 'rgba(37,99,235,0.1)' : 'transparent', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
							<div>{f.name} <span style={{ color: '#6b7280' }}>({f.count})</span></div>
							{f.id !== 1 && (
								<div style={{ display: 'flex', gap: 6 }}>
									<button onClick={(e) => { e.stopPropagation(); setFolderForm({ id: f.id, name: f.name }); setFolderModalVisible(true) }} style={{ border: '1px solid #e5e7eb', background: '#fff', padding: '2px 8px', borderRadius: 6, cursor: 'pointer' }}>重命名</button>
									<button onClick={async (e) => { e.stopPropagation(); const ok = await askConfirm('确定删除该文件夹？规则将移至默认文件夹'); if (!ok) return; const r = await authedFetch(`${getApiBase()}/api/rule-folders/${f.id}`, { method: 'DELETE' }); if (r.ok) { await fetchRuleFolders(); await fetchDetectionRules(searchRule, selectedFolderId); showToast('文件夹已删除', 'success') } }} style={{ border: '1px solid #ef4444', color: '#ef4444', background: '#fff', padding: '2px 8px', borderRadius: 6, cursor: 'pointer' }}>删除</button>
								</div>
							)}
						</div>
					))}
				</div>

				<div style={{ display: 'grid', gridTemplateRows: 'auto 1fr', gap: 12 }}>
					<div style={{ display: 'flex', gap: 8 }}>
						<input value={searchRule} onChange={(e) => setSearchRule(e.target.value)} placeholder="搜索规则名称或描述..." style={{ flex: 1, border: '1px solid #e5e7eb', borderRadius: 8, padding: '8px 12px' }} />
						<button onClick={openRuleAdd} style={{ background: '#2563eb', color: 'white', padding: '8px 14px', borderRadius: 8, border: 'none', cursor: 'pointer' }}>+ 新建规则</button>
					</div>

					<div style={{ background: 'rgba(255,255,255,0.75)', backdropFilter: 'blur(6px)', border: '1px solid rgba(255,255,255,0.35)', borderRadius: 12, padding: 12, maxHeight: 520, overflow: 'auto' }}>
						{detectionRules.map((rule: any) => (
							<div key={rule.id} draggable onDragStart={() => onDragStartRule(rule.id)} style={{ display: 'grid', gridTemplateColumns: '1fr auto', gap: 8, alignItems: 'center', border: '1px solid #e5e7eb', borderRadius: 10, padding: 12, marginBottom: 10 }}>
								<div>
									<div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
										<div style={{ width: 8, height: 8, borderRadius: 999, background: rule.enabled ? '#10b981' : '#9ca3af' }} />
										<div style={{ fontWeight: 600 }}>{rule.name} <span style={{ color: '#6b7280', fontWeight: 400, fontSize: 12 }}>#{rule.id}</span></div>
									</div>
									<div style={{ color: '#6b7280', fontSize: 12, marginTop: 4 }}>{rule.description}</div>
									<div style={{ color: '#374151', fontSize: 12, marginTop: 4 }}>组合：{rule.operator} | 模式数：{(rule.patterns || []).length} | 文件夹：{rule.folder_id}</div>
								</div>
								<div style={{ display: 'flex', gap: 8 }}>
									<button onClick={() => toggleRule(rule.id, rule.enabled)} style={{ background: rule.enabled ? '#059669' : '#9ca3af', color: '#fff', padding: '6px 10px', borderRadius: 6, border: 'none', cursor: 'pointer' }}>{rule.enabled ? '禁用' : '启用'}</button>
									<button onClick={() => openRuleEdit(rule)} style={{ background: '#10b981', color: '#fff', padding: '6px 10px', borderRadius: 6, border: 'none', cursor: 'pointer' }}>编辑</button>
									<button onClick={() => deleteRule(rule.id)} style={{ background: '#ef4444', color: '#fff', padding: '6px 10px', borderRadius: 6, border: 'none', cursor: 'pointer' }}>删除</button>
								</div>
							</div>
						))}
					</div>
				</div>
			</div>

			<Modal visible={ruleModalVisible} title={ruleModalMode === 'add' ? '新建规则' : '编辑规则'} onClose={() => setRuleModalVisible(false)} footer={[
				<button key="cancel" onClick={() => setRuleModalVisible(false)} style={{ background: '#fff', border: '1px solid #e5e7eb', padding: '8px 14px', borderRadius: 8, cursor: 'pointer' }}>取消</button>,
				<button key="ok" disabled={!ruleForm.name || !ruleForm.operator || !ruleForm.patterns} onClick={submitRule} style={{ background: !ruleForm.name || !ruleForm.operator || !ruleForm.patterns ? '#9ca3af' : '#2563eb', color: '#fff', padding: '8px 14px', borderRadius: 8, border: 'none', cursor: !ruleForm.name || !ruleForm.operator || !ruleForm.patterns ? 'not-allowed' : 'pointer' }}>保存</button>
			]}>
				<div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
					<div>
						<div style={{ fontSize: 12, color: '#6b7280' }}>规则名称*</div>
						<input value={ruleForm.name} onChange={(e) => setRuleForm({ ...ruleForm, name: e.target.value })} style={{ width: '100%', border: '1px solid #e5e7eb', borderRadius: 8, padding: '8px 12px' }} />
					</div>
					<div>
						<div style={{ fontSize: 12, color: '#6b7280' }}>所属文件夹</div>
						<select value={ruleForm.folder_id} onChange={(e) => setRuleForm({ ...ruleForm, folder_id: Number(e.target.value) })} style={{ width: '100%', border: '1px solid #e5e7eb', borderRadius: 8, padding: '8px 12px' }}>
							{ruleFolders.map((f: any) => (<option key={f.id} value={f.id}>{f.name}</option>))}
						</select>
					</div>
					<div style={{ gridColumn: '1 / -1' }}>
						<div style={{ fontSize: 12, color: '#6b7280' }}>描述</div>
						<input value={ruleForm.description} onChange={(e) => setRuleForm({ ...ruleForm, description: e.target.value })} style={{ width: '100%', border: '1px solid #e5e7eb', borderRadius: 8, padding: '8px 12px' }} />
					</div>
					<div>
						<div style={{ fontSize: 12, color: '#6b7280' }}>组合</div>
						<select value={ruleForm.operator} onChange={(e) => setRuleForm({ ...ruleForm, operator: e.target.value })} style={{ width: '100%', border: '1px solid #e5e7eb', borderRadius: 8, padding: '8px 12px' }}>
							<option value="OR">或 (任一匹配)</option>
							<option value="AND">与 (全部匹配)</option>
							<option value="NOT">非 (均不匹配)</option>
						</select>
					</div>
					<div>
						<div style={{ fontSize: 12, color: '#6b7280' }}>是否正则</div>
						<select value={ruleForm.is_regex ? '1' : '0'} onChange={(e) => setRuleForm({ ...ruleForm, is_regex: e.target.value === '1' })} style={{ width: '100%', border: '1px solid #e5e7eb', borderRadius: 8, padding: '8px 12px' }}>
							<option value="1">正则</option>
							<option value="0">普通包含</option>
						</select>
					</div>
					<div style={{ gridColumn: '1 / -1' }}>
						<div style={{ fontSize: 12, color: '#6b7280', display: 'flex', justifyContent: 'space-between' }}>
							<span>匹配模式（多行分隔，或用逗号/分号）</span>
							<span style={{ color: '#9ca3af' }}>提示：如使用正则匹配多种写法，可写为 OOM|Out of memory；组合选择 与/或/非 决定多模式关系</span>
						</div>
						<textarea value={ruleForm.patterns} onChange={(e) => setRuleForm({ ...ruleForm, patterns: e.target.value })} style={{ width: '100%', minHeight: 120, border: '1px solid #e5e7eb', borderRadius: 8, padding: 12, fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace' }} />
					</div>
					<div>
						<label style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
							<input type="checkbox" checked={!!ruleForm.enabled} onChange={(e) => setRuleForm({ ...ruleForm, enabled: e.target.checked })} /> 启用该规则
						</label>
					</div>
				</div>
			</Modal>

			<FolderModal />
		</div>
	)

	// 用户管理页面
	const UserManagement = () => (
		<div style={{ padding: '2rem' }}>
			<h2 style={{ fontSize: '1.5rem', fontWeight: 'bold', marginBottom: '1rem' }}>👥 用户管理</h2>
			<div style={{ background: 'rgba(255,255,255,0.75)', backdropFilter: 'blur(6px)', border: '1px solid rgba(255,255,255,0.35)', borderRadius: 12, padding: 16 }}>
				<div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
					<h3 style={{ fontWeight: 600, margin: 0 }}>用户列表</h3>
					<button onClick={openUserAdd} style={{ background: '#2563eb', color: 'white', padding: '8px 14px', borderRadius: 8, border: 'none', cursor: 'pointer' }}>+ 添加用户</button>
				</div>
				<div style={{ border: '1px solid #e5e7eb', borderRadius: 8, overflow: 'hidden', maxHeight: 520, overflowY: 'auto' }}>
					<div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr', background: '#f9fafb', padding: 12, fontWeight: 600 }}>
						<div>用户名</div><div>邮箱</div><div>角色</div><div>操作</div>
					</div>
					{users.map((user) => (
						<div key={user.id} style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr', padding: 12, borderTop: '1px solid #e5e7eb' }}>
							<div>{user.username}</div><div>{user.email}</div><div>{user.role}</div>
							<div style={{ display: 'flex', gap: 8 }}>
								<button onClick={() => openUserEdit(user)} style={{ background: '#10b981', color: 'white', padding: '6px 10px', borderRadius: 6, border: 'none', cursor: 'pointer' }}>编辑</button>
								<button onClick={() => confirmDeleteUser(user.id)} style={{ background: '#ef4444', color: 'white', padding: '6px 10px', borderRadius: 6, border: 'none', cursor: 'pointer' }}>删除</button>
							</div>
						</div>
					))}
				</div>
			</div>

			<Modal visible={userModalVisible} title={userModalMode === 'add' ? '添加用户' : '编辑用户'} onClose={() => setUserModalVisible(false)} footer={[
				<button key="cancel" onClick={() => setUserModalVisible(false)} style={{ background: '#fff', border: '1px solid #e5e7eb', padding: '8px 14px', borderRadius: 8, cursor: 'pointer' }}>取消</button>,
				<button key="ok" disabled={!userForm.username || (userModalMode==='add' && !userForm.password)} onClick={submitUser} style={{ background: !userForm.username || (userModalMode==='add' && !userForm.password) ? '#9ca3af' : '#2563eb', color: '#fff', padding: '8px 14px', borderRadius: 8, border: 'none', cursor: !userForm.username || (userModalMode==='add' && !userForm.password) ? 'not-allowed' : 'pointer' }}>提交</button>
			]}>
				<div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
					<div>
						<div style={{ fontSize: 12, color: '#6b7280' }}>用户名*</div>
						<input value={userForm.username} onChange={(e) => setUserForm({ ...userForm, username: e.target.value })} style={{ width: '100%', border: '1px solid #e5e7eb', borderRadius: 8, padding: '8px 12px' }} />
					</div>
					<div>
						<div style={{ fontSize: 12, color: '#6b7280' }}>邮箱(选填)</div>
						<input value={userForm.email} onChange={(e) => setUserForm({ ...userForm, email: e.target.value })} style={{ width: '100%', border: '1px solid #e5e7eb', borderRadius: 8, padding: '8px 12px' }} />
					</div>
					<div>
						<div style={{ fontSize: 12, color: '#6b7280' }}>角色*</div>
						<select value={userForm.role} onChange={(e) => setUserForm({ ...userForm, role: e.target.value })} style={{ width: '100%', border: '1px solid #e5e7eb', borderRadius: 8, padding: '8px 12px' }}>
							<option value="管理员">管理员</option>
							<option value="普通用户">普通用户</option>
						</select>
					</div>
					{userModalMode === 'add' && (
						<div>
							<div style={{ fontSize: 12, color: '#6b7280' }}>密码*</div>
							<input type="password" value={userForm.password} onChange={(e) => setUserForm({ ...userForm, password: e.target.value })} style={{ width: '100%', border: '1px solid #e5e7eb', borderRadius: 8, padding: '8px 12px' }} />
						</div>
					)}
				</div>
			</Modal>
		</div>
	)

	// 仪表板页面
	const Dashboard = () => (
		<div style={{ padding: '2rem' }}>
			<div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
				<h2 style={{ fontSize: '1.5rem', fontWeight: 'bold', margin: 0 }}>📊 系统仪表板</h2>
				{currentUser && <div style={{ color: '#374151' }}>Hi，<span style={{ fontWeight: 700 }}>{currentUser.username}</span></div>}
			</div>
			<div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '1rem', marginBottom: '2rem' }}>
				{[{ color: '#059669', value: dashboardStats.uploaded_files, label: '已上传文件' }, { color: '#dc2626', value: dashboardStats.detected_issues, label: '检测到错误' }, { color: '#2563eb', value: dashboardStats.detection_rules, label: '检测规则' }, { color: '#8b5cf6', value: Object.values(problemStatsByType).reduce((a,b)=>a+b,0), label: '问题总数' }].map((c, i) => (
					<div key={i} style={{ background: 'rgba(255,255,255,0.75)', backdropFilter: 'blur(6px)', border: '1px solid rgba(255,255,255,0.35)', borderRadius: '0.75rem', boxShadow: '0 10px 30px rgba(2,6,23,0.08)', padding: '1.5rem' }}>
						<h3 style={{ color: c.color, fontSize: '2rem', margin: 0 }}>{c.value}</h3>
						<p style={{ color: '#6b7280', margin: 0 }}>{c.label}</p>
					</div>
				))}
			</div>

			<div style={{ background: 'rgba(255,255,255,0.75)', backdropFilter: 'blur(6px)', border: '1px solid rgba(255,255,255,0.35)', borderRadius: '0.75rem', boxShadow: '0 10px 30px rgba(2,6,23,0.08)', padding: '1.5rem', maxHeight: 280, overflow: 'auto' }}>
				<h3 style={{ fontWeight: 600, marginBottom: '1rem' }}>最近分析结果（双击查看详情）</h3>
				{analysisResults.length > 0 ? (
					analysisResults.slice(-20).reverse().map((result, index) => (
						<div key={index} onDoubleClick={() => openAnalysisDetail(result.file_id, result.filename)} style={{ padding: '0.75rem', border: '1px solid #e5e7eb', borderRadius: '0.25rem', marginBottom: '0.5rem', cursor: 'zoom-in' }}>
							<p style={{ fontWeight: 600, margin: 0 }}>{result.filename}</p>
							<p style={{ color: '#6b7280', fontSize: '0.875rem', margin: 0 }}>发现 {result.summary.total_issues} 个问题 - {new Date(result.analysis_time).toLocaleString()}</p>
						</div>
					))
				) : (<p style={{ color: '#6b7280' }}>暂无分析记录</p>)}
			</div>
		</div>
	)

	// 状态卡颜色/文案
	const getStatusColor = () => backendStatus === 'connected' ? '#059669' : backendStatus === 'connecting' ? '#2563eb' : '#dc2626'
	const getStatusText = () => backendStatus === 'connected' ? '✅ 后端: 运行正常' : backendStatus === 'connecting' ? '🔄 后端: 连接中...' : '❌ 后端: 连接失败'

	// —— 问题库 API ——
	useEffect(() => {
		// 持久化筛选条件
		try {
			const s = localStorage.getItem('problem_filters')
			if (s) { const v = JSON.parse(s); setProblemFilterType(v.type||''); setProblemFilterQuery(v.q||''); setProblemFilterCategory(v.category||'') }
		} catch {}
	}, [])
	useEffect(() => {
		try { localStorage.setItem('problem_filters', JSON.stringify({ type: problemFilterType, q: problemFilterQuery, category: problemFilterCategory })) } catch {}
	}, [problemFilterType, problemFilterQuery, problemFilterCategory])

	const fetchProblems = async (type: string = problemFilterType, q: string = problemFilterQuery, category: string = problemFilterCategory) => {
		try {
			const params = new URLSearchParams(); if (type) params.set('error_type', type); if (q) params.set('q', q); if (category) params.set('category', category)
			const r = await authedFetch(`${getApiBase()}/api/problems?${params.toString()}`)
			if (r.ok) { const d = await r.json(); setProblems(d.problems || []) }
		} catch {}
	}
	const fetchProblemStats = async (types: string[] | null = null) => {
		try {
			const params = types && types.length ? `?types=${encodeURIComponent(types.join(','))}` : ''
			const r = await authedFetch(`${getApiBase()}/api/problems/stats${params}`)
			if (r.ok) { const d = await r.json(); setProblemStatsByType(d.by_type || {}) }
		} catch {}
	}
	const openProblemAdd = () => { setProblemForm({ id: null, title: '', url: '', error_type: problemFilterType || '', category: '' }); setProblemModalVisible(true) }
	const openProblemEdit = (p: any) => { setProblemForm({ id: p.id, title: p.title, url: p.url, error_type: p.error_type }); setProblemModalVisible(true) }
	const submitProblem = async () => {
		try {
			const payload = { title: problemForm.title, url: problemForm.url, error_type: problemForm.error_type }
			let r
			if (problemForm.id) r = await authedFetch(`${getApiBase()}/api/problems/${problemForm.id}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) })
			else r = await authedFetch(`${getApiBase()}/api/problems`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) })
			if (r.ok) { setProblemModalVisible(false); await Promise.all([fetchProblems(problemFilterType, problemFilterQuery, problemFilterCategory), fetchProblemStats(null)]); showToast('问题已保存', 'success') } else showToast('保存失败', 'error')
		} catch { showToast('保存失败', 'error') }
	}
	const deleteProblem = async (id: number) => { const ok = await askConfirm('确定删除该问题？'); if (!ok) return; try { const r = await authedFetch(`${getApiBase()}/api/problems/${id}`, { method: 'DELETE' }); if (r.ok) { await Promise.all([fetchProblems(problemFilterType, problemFilterQuery, problemFilterCategory), fetchProblemStats(null)]); showToast('已删除', 'success') } else showToast('删除失败', 'error') } catch { showToast('删除失败', 'error') } }
	const goToProblems = async (type: string) => { setCurrentPage('problems'); setProblemFilterType(type); await Promise.all([fetchProblems(type, problemFilterQuery, problemFilterCategory), fetchProblemStats([type])]) }

	// 问题库页面
	const ProblemsPage = () => (
		<div style={{ padding: '2rem' }}>
			<h2 style={{ fontSize: '1.5rem', fontWeight: 'bold', marginBottom: '1rem' }}>📚 问题库</h2>
			<div className="ui-card" style={{ padding: 16, marginBottom: 12 }}>
				<div style={{ display: 'grid', gridTemplateColumns: '2fr 2fr 2fr auto auto', gap: 8, alignItems: 'center' }}>
					<input placeholder="按错误类型过滤，如 I/O error" value={problemFilterType} onChange={(e) => setProblemFilterType(e.target.value)} style={{ border: '1px solid #e5e7eb', borderRadius: 8, padding: '8px 12px' }} />
					<input placeholder="按名称/链接模糊查询" value={problemFilterQuery} onChange={(e) => setProblemFilterQuery(e.target.value)} style={{ border: '1px solid #e5e7eb', borderRadius: 8, padding: '8px 12px' }} />
					<input placeholder="问题分类(选填)" value={problemFilterCategory} onChange={(e) => setProblemFilterCategory(e.target.value)} style={{ border: '1px solid #e5e7eb', borderRadius: 8, padding: '8px 12px' }} />
					<button className="btn btn-outline" onClick={() => fetchProblems(problemFilterType, problemFilterQuery, problemFilterCategory)}>查询</button>
					<button className="btn" onClick={() => { setProblemFilterType(''); setProblemFilterQuery(''); setProblemFilterCategory(''); fetchProblems('', '', '') }}>清空</button>
					<button className="btn btn-primary" onClick={openProblemAdd}>+ 新增问题</button>
				</div>
			</div>
			<div className="ui-card" style={{ padding: 16, marginBottom: 12 }}>
				<h4 style={{ marginTop: 0 }}>统计</h4>
				<div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
					{Object.entries(problemStatsByType).map(([k,v]) => (
						<button key={k} className="btn" onClick={() => { setProblemFilterType(k); fetchProblems(k, problemFilterQuery, problemFilterCategory) }} style={{ background: '#fff' }}>{k}（{v}）</button>
					))}
					<button className="btn btn-outline" onClick={() => { setProblemFilterType(''); fetchProblems('', '', '') }}>全部</button>
				</div>
			</div>
							<div className="ui-card" style={{ padding: 0, overflow: 'hidden' }}>
					<div style={{ display: 'grid', gridTemplateColumns: '2fr 3fr 2fr 1fr', background: '#f9fafb', padding: 12, fontWeight: 600 }}>
						<div>问题名称</div><div>链接</div><div>错误类型</div><div>操作</div>
					</div>
					<div style={{ maxHeight: 480, overflow: 'auto' }}>
						{problems.map((p) => (
							<div key={p.id} style={{ display: 'grid', gridTemplateColumns: '2fr 3fr 2fr 1fr', padding: 12, borderTop: '1px solid #e5e7eb' }}>
								<div style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }} title={p.title}>{p.title}</div>
								<div style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }} title={p.url}><a href={p.url} target="_blank" rel="noreferrer" style={{ color: '#2563eb' }}>{p.url}</a></div>
								<div style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }} title={p.error_type}>{p.error_type}</div>
								<div style={{ display: 'flex', gap: 8 }}>
									<button onClick={() => openProblemEdit(p)} className="btn">编辑</button>
									<button onClick={() => deleteProblem(p.id)} className="btn btn-danger">删除</button>
								</div>
							</div>
						))}
					</div>
				</div>
			<Modal visible={problemModalVisible} title={problemForm.id ? '编辑问题' : '新增问题'} onClose={() => setProblemModalVisible(false)} footer={[
				<button key="cancel" className="btn btn-outline" onClick={() => setProblemModalVisible(false)}>取消</button>,
				<button key="ok" className="btn btn-primary" disabled={!problemForm.title || !problemForm.url || !problemForm.error_type} onClick={submitProblem}>保存</button>
			]}>
				<div className="form-grid">
					<div className="form-col"><div className="label">问题名称*</div><input className="ui-input" value={problemForm.title} onChange={(e) => setProblemForm({ ...problemForm, title: e.target.value })} /></div>
					<div className="form-col"><div className="label">问题链接*</div><input className="ui-input" value={problemForm.url} onChange={(e) => setProblemForm({ ...problemForm, url: e.target.value })} /></div>
					<div className="form-col"><div className="label">问题类型*</div><select className="ui-select" value={problemForm.error_type} onChange={(e) => setProblemForm({ ...problemForm, error_type: e.target.value })}>{detectionRules.map((r:any)=>(<option key={r.id} value={(r.patterns?.[0]||r.name)}>{r.name}（{r.description}）</option>))}</select></div>
				</div>
			</Modal>
		</div>
	)

	return (
		<div style={{ minHeight: '100vh', background: 'radial-gradient(1200px 600px at -10% -10%, #c7d2fe 0%, transparent 60%), radial-gradient(1200px 600px at 110% -10%, #bbf7d0 0%, transparent 60%), linear-gradient(180deg, #f8fafc 0%, #eef2ff 100%)' }}>
			<Nav />
			{currentUser ? (currentPage === 'dashboard' ? Dashboard() : currentPage === 'logs' ? LogManagement() : currentPage === 'rules' ? RuleManagement() : currentPage === 'problems' ? ProblemsPage() : UserManagement()) : (
				<div style={{ padding: '2rem', color: '#6b7280' }}>请先登录以使用平台功能。</div>
			)}

			<div onClick={() => setCardExpanded(v => !v)} title={cardExpanded ? '点击收起' : '点击展开'} style={{ position: 'fixed', bottom: 16, right: 16, background: 'rgba(255,255,255,0.9)', backdropFilter: 'blur(8px)', border: '1px solid rgba(255,255,255,0.6)', borderRadius: 12, boxShadow: '0 20px 60px rgba(2,6,23,0.15)', padding: cardExpanded ? 16 : 0, width: cardExpanded ? 360 : 8, height: cardExpanded ? 'auto' : 140, transition: 'all .25s ease', cursor: 'pointer', zIndex: 60, overflow: 'hidden' }}>
				<div style={{ opacity: cardExpanded ? 1 : 0, transition: 'opacity .2s ease', padding: cardExpanded ? 0 : 0 }}>
					<div style={{ fontSize: 14 }}>
						<div style={{ color: '#059669', fontWeight: 700 }}>✅ 前端: 运行正常</div>
						<div style={{ color: getStatusColor(), fontWeight: 700 }}>{getStatusText()}</div>
					</div>
				</div>
			</div>

			{/* 登录弹窗已弃用：统一跳转 /login */}
			{false && <Modal visible={false} title="登录" onClose={() => {}} footer={[]} />}

			{/* 个人中心 */}
			<ProfileModal />
			<FolderModal />

			<Toasts toasts={toasts} remove={removeToast} />
			<ConfirmModal visible={confirmState.visible} text={confirmState.text} onConfirm={() => { confirmState.resolve && confirmState.resolve(true); setConfirmState({ visible: false, text: '', resolve: null }) }} onCancel={() => { confirmState.resolve && confirmState.resolve(false); setConfirmState({ visible: false, text: '', resolve: null }) }} />
			{/* 全局分析详情 Modal：支持从任何页面打开 */}
			<Modal visible={detailVisible} title={detailData?.title || '分析详情'} onClose={() => setDetailVisible(false)}>
				{detailData && (() => {
					const groups: Record<string, any[]> = {}
					for (const it of detailData.data.issues || []) {
						const typeKey = String(it.matched_text || it.rule_name || '其他')
						const zh = String(it.description || '')
						const key = `${typeKey}||${zh}`
						groups[key] = groups[key] || []
						groups[key].push(it)
					}
					const entries = Object.entries(groups)
					return (
						<div style={{ maxHeight: '65vh', overflow: 'auto', fontFamily: 'ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Noto Sans, Ubuntu, Cantarell, Helvetica Neue, Arial' }}>
							<div style={{ color: '#6b7280', fontSize: 12, marginBottom: 8 }}>共 {detailData.data.summary.total_issues} 个问题，{entries.length} 个类型</div>
							{entries.map(([key, list], gi) => {
								const [typeKey, zh] = key.split('||')
								return (
									<div key={gi} style={{ border: '1px solid #e5e7eb', borderRadius: 10, padding: 10, marginBottom: 10 }}>
										<div onClick={() => setCollapsedGroups(v => ({ ...v, [key]: !v[key] }))} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', cursor: 'pointer', userSelect: 'none' }}>
											<div style={{ fontWeight: 800, color: '#111827' }}>{typeKey} <span style={{ marginLeft: 8, color: '#ef4444', fontWeight: 700 }}>{zh}</span></div>
											<div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
												<span style={{ color: '#6b7280', fontSize: 12 }}>{collapsedGroups[key] ? '点击展开' : '点击折叠'} · {list.length}</span>
												<span style={{ color: '#6b7280', fontSize: 12 }}>问题库：{problemStatsByType[typeKey] || 0}</span>
												<button onClick={(e) => { e.stopPropagation(); goToProblems(typeKey) }} style={{ border: '1px solid #e5e7eb', background: '#fff', padding: '4px 8px', borderRadius: 6, cursor: 'pointer' }}>查看</button>
											</div>
										</div>
										{!collapsedGroups[key] && (
											<div className="stack-12" style={{ marginTop: 8 }}>
												{list.map((it: any, idx: number) => (
													<div key={idx} style={{ border: '1px solid #e5e7eb', borderRadius: 8, padding: 10 }}>
														<div style={{ fontWeight: 600 }}><span style={{ color: '#ef4444', fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace' }}>{it.matched_text}</span> <span style={{ color: '#6b7280', fontWeight: 400 }}>#{it.line_number}</span></div>
														<pre style={{ whiteSpace: 'pre-wrap', background: '#f9fafb', padding: 8, borderRadius: 6, marginTop: 6, fontSize: 12, fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace' }}>{it.context}</pre>
												</div>
												))}
											</div>
										)}
									</div>
								)
							})}
						</div>
					)
				})()}
			</Modal>
		</div>
	)
}

function ProfileCenter({ currentUser, onLogout }: any) {
	const [visible, setVisible] = useState(false)
	const [form, setForm] = useState({ old_password: '', new_password: '' })
	const getApiBase = () => (typeof window !== 'undefined' ? `${window.location.protocol}//${window.location.hostname}:8001` : '')
	const getStoredToken = () => (typeof window !== 'undefined' ? (localStorage.getItem('token') || sessionStorage.getItem('token') || '') : '')
	const showToast = (msg: string, type: 'success' | 'error' | 'info' = 'info') => {
		const event = new CustomEvent('toast', { detail: { msg, type } })
		window.dispatchEvent(event as any)
	}
	useEffect(() => {
		const handler = (e: any) => {}
		window.addEventListener('toast', handler as any)
		return () => window.removeEventListener('toast', handler as any)
	}, [])
	const submit = async () => {
		try {
			const r = await fetch(`${getApiBase()}/api/auth/change_password`, { method: 'POST', headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${getStoredToken()}` }, body: JSON.stringify(form) })
			if (r.ok) { setVisible(false); showToast('密码已更新，请重新登录', 'success'); onLogout() } else { showToast('更新失败', 'error') }
		} catch { showToast('更新失败', 'error') }
	}
	if (!currentUser) return null
	return (
		<>
			<button onClick={() => setVisible(true)} style={{ display: 'none' }} id="open-profile-modal" />
			<Modal visible={visible} title="个人中心" onClose={() => setVisible(false)} footer={[
				<button key="logout" onClick={onLogout} style={{ background: '#ef4444', color: '#fff', padding: '8px 14px', borderRadius: 8, border: 'none', cursor: 'pointer' }}>退出登录</button>,
				<button key="ok" onClick={submit} style={{ background: '#2563eb', color: '#fff', padding: '8px 14px', borderRadius: 8, border: 'none', cursor: 'pointer' }}>修改密码</button>
			]}>
				<div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: 12, minWidth: 360 }}>
					<div style={{ color: '#374151' }}>当前用户：<b>{currentUser.username}</b></div>
					<div>
						<div style={{ fontSize: 12, color: '#6b7280' }}>原密码</div>
						<input type="password" value={form.old_password} onChange={(e) => setForm({ ...form, old_password: e.target.value })} style={{ width: '100%', border: '1px solid #e5e7eb', borderRadius: 8, padding: '8px 12px' }} />
					</div>
					<div>
						<div style={{ fontSize: 12, color: '#6b7280' }}>新密码</div>
						<input type="password" value={form.new_password} onChange={(e) => setForm({ ...form, new_password: e.target.value })} style={{ width: '100%', border: '1px solid #e5e7eb', borderRadius: 8, padding: '8px 12px' }} />
					</div>
				</div>
			</Modal>
		</>
	)
}
  