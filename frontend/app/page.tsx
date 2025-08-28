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
	const overlayDown = useRef(false)
	return (
		<div
			style={{ position: 'fixed', inset: 0, background: 'rgba(15, 23, 42, 0.45)', backdropFilter: 'blur(6px)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 50 }}
			onMouseDown={(e) => { if (e.target === e.currentTarget) overlayDown.current = true }}
			onMouseUp={(e) => { if (overlayDown.current && e.target === e.currentTarget) onClose(); overlayDown.current = false }}
		>
			<div className="ui-card" onMouseDown={(e) => e.stopPropagation()} onMouseUp={(e) => e.stopPropagation()} style={{ width: 'min(920px, 94vw)', maxHeight: '86vh', overflow: 'auto' }}>
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
	const [allDetectionRules, setAllDetectionRules] = useState<any[]>([])
	const [ruleFolders, setRuleFolders] = useState<any[]>([])
	const [selectedFolderId, setSelectedFolderId] = useState<number | null>(null)
	const [searchRule, setSearchRule] = useState('')
	const [draggingRuleId, setDraggingRuleId] = useState<number | null>(null)
	const [backendStatus, setBackendStatus] = useState<'connected' | 'connecting' | 'failed'>('connecting')
	const [analysisResults, setAnalysisResults] = useState<any[]>([])
	const [highlightAnalysisId, setHighlightAnalysisId] = useState<number | null>(null)
	const [viewHighlightId, setViewHighlightId] = useState<number | null>(null)
	const [users, setUsers] = useState<any[]>([])

	// —— 问题库：状态 ——
	const [problems, setProblems] = useState<any[]>([])
	const [problemModalVisible, setProblemModalVisible] = useState(false)
	const [problemForm, setProblemForm] = useState<any>({ id: null, title: '', url: '', error_type: '' })
	const [problemFilterType, setProblemFilterType] = useState<string>('')
	const [problemFilterQuery, setProblemFilterQuery] = useState<string>('')
	const [problemFilterCategory, setProblemFilterCategory] = useState<string>('')
	const [problemStatsByType, setProblemStatsByType] = useState<Record<string, number>>({})
	const [highlightProblemId, setHighlightProblemId] = useState<number | null>(null)
	const [statsExpanded, setStatsExpanded] = useState(false)
	const [problemPage, setProblemPage] = useState(1)
	const [problemTypeQuery, setProblemTypeQuery] = useState('')
	const PROBLEM_PAGE_SIZE = 200
	const [problemSort, setProblemSort] = useState<{ key: 'error_type' | ''; order: 'asc' | 'desc' }>({ key: '', order: 'asc' })

	// 规范化字符串用于搜索（去除非字母数字与中文，统一小写）
	const normalizeForSearch = (s: string) => String(s || '')
		.toLowerCase()
		.replace(/[^a-z0-9\u4e00-\u9fa5]/g, '')

	// 确保已加载全量规则列表（不受文件夹/搜索过滤）
	const ensureAllRulesLoaded = async () => {
		if (allDetectionRules && allDetectionRules.length > 0) return
		try {
			const r = await authedFetch(`${getApiBase()}/api/rules`)
			if (r.ok) {
				const d = await r.json()
				setAllDetectionRules(d.rules || [])
			}
		} catch {}
	}

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

	// 分析状态管理
	const [analyzingFiles, setAnalyzingFiles] = useState<Set<number>>(new Set())
	const [analysisProgress, setAnalysisProgress] = useState<Record<number, { progress: number; message: string }>>({})
	const [analyzingText, setAnalyzingText] = useState(false)
	const [textAnalysisProgress, setTextAnalysisProgress] = useState({ progress: 0, message: '' })
	
	// 预览弹窗
	const [pasteText, setPasteText] = useState('')
	const [previewVisible, setPreviewVisible] = useState(false)
	const [previewTitle, setPreviewTitle] = useState('')
	const [previewContent, setPreviewContent] = useState('')
	const [previewMode, setPreviewMode] = useState<'shell' | 'txt'>('shell')
	const [previewSearch, setPreviewSearch] = useState('')
	const [debouncedPreviewSearch, setDebouncedPreviewSearch] = useState('')
	const [enableHighlight, setEnableHighlight] = useState(true)
	const MAX_HIGHLIGHT_BYTES = 300000
	const previewContainerRef = useRef<HTMLDivElement | null>(null)
	const [currentMatchIndex, setCurrentMatchIndex] = useState(0)
	useEffect(() => {
		const t = setTimeout(() => setDebouncedPreviewSearch(previewSearch), 300)
		return () => clearTimeout(t)
	}, [previewSearch])
	useEffect(() => { setEnableHighlight(previewContent.length <= MAX_HIGHLIGHT_BYTES) }, [previewContent])
	const previewMatches = useMemo(() => {
		if (!debouncedPreviewSearch || !enableHighlight) return 0
		try { const slice = previewContent.slice(0, MAX_HIGHLIGHT_BYTES); const re = new RegExp(debouncedPreviewSearch.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'ig'); return (slice.match(re) || []).length } catch { return 0 }
	}, [debouncedPreviewSearch, previewContent, enableHighlight])
	useEffect(() => { setCurrentMatchIndex(0) }, [previewSearch, previewVisible])
	const jumpMatch = (delta: number) => {
		const cont = previewContainerRef.current
		if (!cont) return
		if (!enableHighlight) return
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
	const [pageByGroup, setPageByGroup] = useState<Record<string, number>>({})
	const PAGE_SIZE_PER_GROUP = 300
	useEffect(() => { if (detailVisible) setCollapsedGroups({}) }, [detailVisible])
	useEffect(() => {
		if (!detailVisible || !detailData?.data?.issues) return
		// 使用规则名称而不是匹配文本来统计问题类型
		const types = Array.from(new Set((detailData.data.issues || []).map((it: any) => String(it.rule_name || '其他'))))
		fetchProblemStats(types)
		// 打开详情时重置每组页码
		setPageByGroup({})
	}, [detailVisible, detailData])

	// 用户/规则弹窗
	const [userModalVisible, setUserModalVisible] = useState(false)
	const [userModalMode, setUserModalMode] = useState<'add' | 'edit'>('add')
	const [userForm, setUserForm] = useState<any>({ id: null, username: '', email: '', password: '', role: '普通用户' })
	const [ruleModalVisible, setRuleModalVisible] = useState(false)
	const [ruleModalMode, setRuleModalMode] = useState<'add' | 'edit'>('add')
	const [ruleForm, setRuleForm] = useState<any>({ id: null, name: '', description: '', enabled: true, patterns: '', dsl: '', folder_id: 1 })
	const [folderModalVisible, setFolderModalVisible] = useState(false)
	const [folderForm, setFolderForm] = useState<any>({ id: null, name: '' })

	// 数据缓存状态
	const [dataCache, setDataCache] = useState({
		dashboardStats: null,
		uploadedFiles: null,
		ruleFolders: null,
		detectionRules: null,
		users: null,
		analysisResults: null,
		problems: null,
		problemStats: null
	})

	// 状态卡
	const [cardExpanded, setCardExpanded] = useState(true)
	useEffect(() => {
		const timer = setTimeout(() => setCardExpanded(false), 10000)
		return () => clearTimeout(timer)
	}, [])

	const checkBackendStatus = async (base?: string) => {
		try {
			if (typeof window === 'undefined') return false
			const protocol = window.location.protocol
			const host = window.location.hostname
			const urlBase = base || `${protocol}//${host}:8001`
			const controller = new AbortController()
			const timer = setTimeout(() => controller.abort(), 5000)
			try {
				const r = await fetch(`${urlBase}/health`, { signal: controller.signal })
				clearTimeout(timer)
				if (r.ok) { setApiBase(urlBase); setBackendStatus('connected'); return true }
			} catch {
				clearTimeout(timer)
			}
			setBackendStatus('failed');
			return false
		} catch { setBackendStatus('failed'); return false }
	}
	const fetchDashboardStats = async (useCache = true) => { 
		if (useCache && dataCache.dashboardStats) return
		try { 
			const r = await authedFetch(`${getApiBase()}/api/dashboard/stats`)
			if (r.ok) {
				const data = await r.json()
				setDashboardStats(data)
				setDataCache(prev => ({ ...prev, dashboardStats: data }))
			}
		} catch {} 
	}
	const fetchUploadedFiles = async (useCache = true) => { 
		if (useCache && dataCache.uploadedFiles) return
		try { 
			const r = await authedFetch(`${getApiBase()}/api/logs`)
			if (r.ok) { 
				const d = await r.json()
				const files = (d.files || []).sort((a:any,b:any)=> new Date(b.upload_time).getTime() - new Date(a.upload_time).getTime())
				setUploadedFiles(files)
				setDataCache(prev => ({ ...prev, uploadedFiles: files }))
			} 
		} catch {} 
	}
	const fetchDetectionRules = async (q = '', folderId: number | null = null) => { try { const params = new URLSearchParams(); if (q) params.set('query', q); if (folderId !== null) params.set('folder_id', String(folderId)); const r = await authedFetch(`${getApiBase()}/api/rules?${params.toString()}`); if (r.ok) { const d = await r.json(); const rules = (d.rules || []).sort((a:any,b:any)=> (b.id||0) - (a.id||0)); setDetectionRules(rules); setAllDetectionRules(prev => (prev && prev.length >= rules.length ? prev : rules)) } } catch {} }
	const fetchRuleFolders = async () => { try { const r = await authedFetch(`${getApiBase()}/api/rule-folders`); if (r.ok) { const d = await r.json(); const folders = (d.folders || []).sort((a:any,b:any)=> (b.id||0) - (a.id||0)); setRuleFolders(folders); if (folders && folders.length && selectedFolderId === null) setSelectedFolderId(folders[0].id) } } catch {} }
	const fetchUsers = async () => { try { const r = await authedFetch(`${getApiBase()}/api/users`); if (r.ok) { const d = await r.json(); setUsers(d.users || []) } } catch {} }
	const fetchMe = async () => { try { const r = await authedFetch(`${getApiBase()}/api/auth/me`); if (r.ok) { const d = await r.json(); setCurrentUser(d.user) } } catch {} }
	const fetchAnalysisResults = async () => { try { const r = await authedFetch(`${getApiBase()}/api/analysis/results`); if (r.ok) { const d = await r.json(); setAnalysisResults(d.results || []) } } catch {} }

	useEffect(() => {
		const base = computeApiBase(); setApiBase(base)
		;(async () => { 
			const ok = await checkBackendStatus(base)
			if (ok) { 
				await fetchMe()
				// 只加载基础数据，其他数据按需加载
				await Promise.all([
					fetchRuleFolders()
				])
			} 
		})()
	}, [])

	// 按需加载数据的 useEffect
	useEffect(() => { 
		if (apiBase && currentUser) { 
			// 根据当前页面按需加载数据
			switch (currentPage) {
				case 'dashboard':
					fetchDashboardStats()
					fetchAnalysisResults()
					break
				case 'logs':
					fetchUploadedFiles()
					break
				case 'rules':
					fetchDetectionRules(searchRule, selectedFolderId)
					break
				case 'problems':
					fetchProblems(problemFilterType, problemFilterQuery, problemFilterCategory)
					fetchProblemStats(null)
					ensureAllRulesLoaded()
					break
				case 'users':
					fetchUsers()
					break
			}
		} 
	}, [apiBase, currentUser, currentPage])

	// 搜索相关的 useEffect（添加防抖动）
	useEffect(() => {
		if (!apiBase || !currentUser) return
		
		const timeoutId = setTimeout(() => {
			if (currentPage === 'rules') {
				fetchDetectionRules(searchRule, selectedFolderId)
			}
		}, 300) // 300ms 防抖动

		return () => clearTimeout(timeoutId)
	}, [searchRule, selectedFolderId, apiBase, currentUser, currentPage])

	// —— 交互与业务辅助 ——
	const askConfirm = (text: string) => openConfirm(text)
	const parsePatterns = (s: string) => (s || '').split(/\r?\n|,|;|、/).map(v => v.trim()).filter(Boolean)

	// 预览高亮渲染
	const renderHighlighted = (text: string, q: string) => {
		if (!q || !enableHighlight) return (<pre style={{ margin: 0, whiteSpace: 'pre-wrap' }}>{text}</pre>)
		try {
			const slice = text.slice(0, MAX_HIGHLIGHT_BYTES)
			const re = new RegExp(q.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'gi')
			const html = slice.replace(re, (m) => `<mark style="background:#fde68a">${m}</mark>`) + (text.length > MAX_HIGHLIGHT_BYTES ? `\n\n【提示】内容较大（${(text.length/1024).toFixed(0)}KB），仅对前 ${(MAX_HIGHLIGHT_BYTES/1024).toFixed(0)}KB 启用高亮。` : '')
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
				if (!r.ok) { const msg = await r.text(); throw new Error(msg||'上传失败') }
			}
			// 只刷新需要的数据
			if (currentPage === 'logs') {
				await fetchUploadedFiles(false) // 强制刷新
			}
			if (currentPage === 'dashboard') {
				await fetchDashboardStats(false) // 强制刷新
			}
			showToast('文件上传成功', 'success')
		} catch {
			showToast('文件上传失败，可能超过服务器限制或网络异常', 'error')
		} finally {
			try { e.target.value = '' } catch {}
		}
	}
	const handleAnalyzeText = async () => {
		try {
			if (!pasteText) return showToast('请先粘贴内容', 'info')
			
			// 启动分析状态
			setAnalyzingText(true)
			setTextAnalysisProgress({ progress: 0, message: '开始分析粘贴内容...' })
			
			const textSizeKB = new Blob([pasteText]).size / 1024
			const estimatedTime = Math.max(2, Math.min(10, Math.ceil(textSizeKB / 150))) // 每150KB约1秒，最少2秒，最多10秒
			showToast(`开始分析文本内容，预计耗时 ${estimatedTime} 秒`, 'info')
			
			// 开始分析请求
			const analysisPromise = authedFetch(`${getApiBase()}/api/logs/analyze_text`, { 
				method: 'POST', 
				headers: { 'Content-Type': 'application/json' }, 
				body: JSON.stringify({ text: pasteText, filename: 'pasted.log' }) 
			})
			
			// 进度模拟器 - 优化性能
			let currentProgress = 0
			const progressInterval = setInterval(() => {
				currentProgress += Math.random() * 25 + 15 // 每次增加15-40%，加快进度
				if (currentProgress > 85) currentProgress = 85 // 最多到85%，等待实际完成
				
				const progressMessages = [
					'正在处理文本内容...',
					'正在应用检测规则...',
					'正在分析文本模式...',
					'即将完成分析...'
				]
				const messageIndex = Math.floor((currentProgress / 100) * progressMessages.length)
				
				setTextAnalysisProgress({ 
					progress: currentProgress, 
					message: progressMessages[Math.min(messageIndex, progressMessages.length - 1)]
				})
			}, Math.max(600, estimatedTime * 1000 / 5)) // 最少600ms更新一次，提升性能
			
			const r = await analysisPromise
			clearInterval(progressInterval)
			
			if (r.ok) {
				const d = await r.json()
				
				// 调试：打印返回的数据结构
				console.log('文本分析结果数据：', d)
				console.log('文本分析结果数据结构检查：', {
					'd.summary?.total_issues': d.summary?.total_issues,
					'd.data?.summary?.total_issues': d.data?.summary?.total_issues, 
					'd.issues?.length': d.issues?.length,
					'd.data?.issues?.length': d.data?.issues?.length,
					'd.total_issues': d.total_issues,
					'd.data?.total_issues': d.data?.total_issues
				})
				
				setTextAnalysisProgress({ progress: 100, message: '分析完成！正在跳转...' })
				
				// 短暂延迟让用户看到完成状态
				setTimeout(async () => {
					setAnalysisResults(prev => [...prev.filter(x => x.file_id !== d.file_id), d])
					await Promise.all([fetchUploadedFiles(false), fetchDashboardStats(false), fetchAnalysisResults()])
					setPasteText('')
					
					// 清理状态
					setAnalyzingText(false)
					setTextAnalysisProgress({ progress: 0, message: '' })
					
					// 多种方式获取问题数量
					const totalIssues = d.summary?.total_issues || d.data?.summary?.total_issues || d.issues?.length || d.data?.issues?.length || d.total_issues || d.data?.total_issues || 0
					showToast(`文本分析完成！发现 ${totalIssues} 个问题`, 'success')
					
					// 跳转到仪表板
					setCurrentPage('dashboard')
					setHighlightAnalysisId(d.file_id)
					setTimeout(() => setHighlightAnalysisId(null), 5000)
				}, 400) // 400ms延迟，加快跳转
			} else {
				setAnalyzingText(false)
				setTextAnalysisProgress({ progress: 0, message: '' })
				showToast('分析失败', 'error')
			}
		} catch (error) { 
			setAnalyzingText(false)
			setTextAnalysisProgress({ progress: 0, message: '' })
			showToast('分析失败', 'error') 
		}
	}
	const analyzeFile = async (fileId: number) => {
		try { 
			// 获取文件信息估算处理时间 - 更准确的时间预估
			const fileInfo = uploadedFiles.find(f => f.id === fileId)
			const fileSizeKB = fileInfo?.size ? fileInfo.size / 1024 : 0
			const estimatedTime = Math.max(3, Math.min(20, Math.ceil(fileSizeKB / 300))) // 每300KB约1秒，最少3秒，最多20秒
			// 标记文件为分析中状态
			setAnalyzingFiles(prev => new Set(prev.add(fileId)))
			setAnalysisProgress(prev => ({ 
				...prev, 
				[fileId]: { progress: 0, message: `开始分析 ${fileInfo?.filename || '文件'}...` }
			}))
			// 显示分析开始提示（仅提示开始，不再预估数量）
			showToast(`开始分析文件，预计耗时约 ${estimatedTime} 秒`, 'info')
			// 开始分析请求
			const analysisPromise = authedFetch(`${getApiBase()}/api/logs/${fileId}/analyze`, { method: 'POST' })
			// 进度模拟器（视觉进度），上限85%
			let currentProgress = 0
			const progressInterval = setInterval(() => {
				currentProgress += Math.random() * 20 + 10
				if (currentProgress > 85) currentProgress = 85
				const progressMessages = [
					'正在读取文件内容...',
					'正在应用检测规则...',
					'正在分析日志模式...',
					'正在生成分析报告...',
					'即将完成分析...'
				]
				const messageIndex = Math.floor((currentProgress / 100) * progressMessages.length)
				setAnalysisProgress(prev => ({ 
					...prev, 
					[fileId]: { progress: currentProgress, message: progressMessages[Math.min(messageIndex, progressMessages.length - 1)] }
				}))
			}, Math.max(800, estimatedTime * 1000 / 6))
			// 等待后端接受
			const r = await analysisPromise
			if (!r.ok) throw new Error('start_failed')
			// 轮询状态直到 ready，然后获取真实结果
			const pollStatus = async (): Promise<any> => {
				for (let i = 0; i < 60; i++) { // 最多轮询60次（~60s）
					await new Promise(res => setTimeout(res, 1000))
					try { 
						const sr = await authedFetch(`${getApiBase()}/api/analysis/${fileId}/status`)
						if (sr.ok) { 
							const s = await sr.json()
							if (s.status === 'ready') {
								const rr = await authedFetch(`${getApiBase()}/api/analysis/${fileId}`)
								if (rr.ok) return await rr.json()
							}
						}
					} catch {}
				}
				throw new Error('timeout')
			}
			const d = await pollStatus()
			clearInterval(progressInterval)
				// 完成进度显示
			setAnalysisProgress(prev => ({ ...prev, [fileId]: { progress: 100, message: '分析完成！' } }))
			// 更新分析结果与统计
				setAnalysisResults(prev => [...prev.filter(x => x.file_id !== d.file_id), d])
			await Promise.all([fetchDashboardStats(false), fetchAnalysisResults()])
			// 清理状态
			setAnalyzingFiles(prev => { const n = new Set(prev); n.delete(fileId); return n })
			setAnalysisProgress(prev => { const { [fileId]: _, ...rest } = prev; return rest })
			// 使用真实数量
			const totalIssues = d?.summary?.total_issues || 0
					showToast(`分析完成！发现 ${totalIssues} 个问题`, 'success')
			// 跳转并高亮
			setCurrentPage('dashboard'); setHighlightAnalysisId(d.file_id); setTimeout(() => setHighlightAnalysisId(null), 5000)
			setTimeout(() => { try { const el = document.querySelector(`[data-analysis-id="${d.file_id}"]`) as HTMLElement; if (el) el.scrollIntoView({ block: 'center' }) } catch {} }, 100)
		} catch (error) { 
			setAnalyzingFiles(prev => { const n = new Set(prev); n.delete(fileId); return n })
			setAnalysisProgress(prev => { const { [fileId]: _, ...rest } = prev; return rest })
				showToast('分析失败，请重试', 'error')
		}
	}
	const deleteFile = async (fileId: number) => {
		const ok = await askConfirm('确定删除该日志文件？')
		if (!ok) return
		try { 
			const r = await authedFetch(`${getApiBase()}/api/logs/${fileId}`, { method: 'DELETE' })
			if (r.ok) { 
				// 强制刷新文件列表和统计数据
				await Promise.all([fetchUploadedFiles(false), fetchDashboardStats(false)])
				// 同时更新分析结果列表
				setAnalysisResults(prev => prev.filter(x => x.file_id !== fileId))
				showToast('删除成功', 'success') 
			} else showToast('删除失败', 'error') 
		} catch { 
			showToast('删除失败', 'error') 
		}
	}
	const openFilePreview = async (fileId: number, filename: string) => {
		try {
			// 使用分片预览接口，首次加载从0开始
			const r = await authedFetch(`${getApiBase()}/api/logs/${fileId}/preview?offset=0&size=${512*1024}`)
			if (r.ok) { 
				const d = await r.json()
				setPreviewTitle(`${d.filename}`)
				setPreviewContent(d.chunk || '')
				setPreviewMode('shell')
				setPreviewVisible(true)
				// 将下一次偏移保存在 window 作用域（简单实现）
				;(window as any).__preview_state__ = { fileId, nextOffset: d.next_offset, total: d.total_size }
			}
		} catch {}
	}
	const openAnalysisDetail = async (fileId: number, filename: string) => {
		try { const r = await authedFetch(`${getApiBase()}/api/analysis/${fileId}`); if (r.ok) { const d = await r.json(); 
			// 简化标题：仅显示规则名称和描述（不显示具体的匹配内容）
			let title = '分析详情';
			if (d.issues && d.issues.length > 0) {
				const pick = d.issues.find((i: any) => i?.severity === 'high') || d.issues[0];
				const name = String(pick?.rule_name || '问题');
				const desc = String(pick?.description || '');
				// 只显示规则名称和描述，不显示具体匹配的内容
				title = desc ? `${name}: ${desc}` : name;
			}
			setDetailData({ title, data: d }); setDetailVisible(true); setCurrentPage('dashboard'); setViewHighlightId(fileId); setTimeout(()=>setViewHighlightId(null), 10000); setTimeout(()=>{ try { const el = document.querySelector(`[data-analysis-id="${fileId}"]`) as HTMLElement; if (el) el.scrollIntoView({ block: 'center' }) } catch {} }, 100) } } catch { showToast('详情加载失败', 'error') }
	}

	// —— 规则：增删改查/拖拽 ——
	const openRuleAdd = () => { setRuleForm({ id: null, name: '', description: '', enabled: true, patterns: '', dsl: '', folder_id: ruleFolders[0]?.id || 1 }); setRuleModalMode('add'); setRuleModalVisible(true) }
	const openRuleEdit = (rule: any) => { setRuleForm({ id: rule.id, name: rule.name, description: rule.description || '', enabled: !!rule.enabled, patterns: (rule.patterns || []).join('\n'), dsl: (rule.dsl || ''), folder_id: rule.folder_id || 1 }); setRuleModalMode('edit'); setRuleModalVisible(true) }
	const submitRule = async () => {
		try {
			const base: any = { name: ruleForm.name, description: ruleForm.description || '', enabled: !!ruleForm.enabled, folder_id: ruleForm.folder_id || 1 }
			const dsl = (ruleForm.dsl || '').trim()
			if (dsl) {
				base.dsl = dsl
			} else {
				base.patterns = parsePatterns(ruleForm.patterns)
			}
			let r
			if (ruleModalMode === 'add') r = await authedFetch(`${getApiBase()}/api/rules`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(base) })
			else r = await authedFetch(`${getApiBase()}/api/rules/${ruleForm.id}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(base) })
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
			<div className="flex items-center space-x-3">
				<div className="w-10 h-10 bg-gradient-to-br from-blue-600 to-violet-600 rounded-xl flex items-center justify-center shadow-lg">
					<span className="text-white font-bold text-lg">📊</span>
				</div>
				<h1 style={{ fontSize: '1.25rem', fontWeight: 800, margin: 0, background: 'linear-gradient(135deg, #1f2937, #3b82f6)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>日志分析平台</h1>
			</div>
			<div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
				{[
					{ id: 'dashboard', label: '📊 仪表板', color: 'from-blue-500 to-indigo-600' },
					{ id: 'logs', label: '📁 日志管理', color: 'from-orange-500 to-red-600' },
					{ id: 'rules', label: '🔍 规则管理', color: 'from-emerald-500 to-teal-600' },
					{ id: 'problems', label: '📚 问题库', color: 'from-purple-500 to-indigo-600' },
					{ id: 'users', label: '👥 用户管理', color: 'from-green-500 to-emerald-600' }
				].map(nav => (
					<button 
						key={nav.id} 
						onClick={() => setCurrentPage(nav.id)} 
						className={`relative px-4 py-2.5 rounded-xl font-semibold text-sm transition-all duration-300 transform hover:scale-105 ${
							currentPage === nav.id 
								? `bg-gradient-to-r ${nav.color} text-white shadow-lg shadow-${nav.color.split('-')[1]}-500/25`
								: 'bg-white/80 text-gray-700 hover:bg-white hover:shadow-md border border-gray-100'
						}`}
						style={{
							backdropFilter: currentPage === nav.id ? 'none' : 'blur(10px)',
						}}
					>
						<span className="relative z-10">{nav.label}</span>
						{currentPage === nav.id && (
							<div className="absolute inset-0 bg-gradient-to-r opacity-10 rounded-xl animate-pulse"></div>
						)}
					</button>
				))}
				<div className="h-8 w-px bg-gray-200 mx-2"></div>
				<button 
					onClick={() => window.location.href = '/profile'} 
					className="px-4 py-2.5 bg-white/80 border border-gray-200 rounded-xl text-gray-700 font-medium hover:bg-white hover:shadow-md transition-all duration-200 backdrop-blur-sm"
				>
					个人中心
				</button>
			</div>
		</nav>
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
			<button key="ok" className="btn btn-primary" disabled={!ruleForm.name || !(((ruleForm.dsl||'').trim()) || ((ruleForm.patterns||'').trim()))} onClick={submitRule}>保存</button>
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
				<div className="form-col" style={{ gridColumn: '1 / -1' }}>
					<div className="label">规则表达式（DSL）</div>
					<textarea className="ui-input" style={{ minHeight: 120 }} value={ruleForm.dsl} onChange={(e) => setRuleForm({ ...ruleForm, dsl: e.target.value })} placeholder='使用 | & ! () 和引号短语，例如：
OOM | "Out of memory"
("No space left" | "disk full") !write
(("No space left" | "disk full") !write) & "space error"' />
					<div style={{ color: '#6b7280', fontSize: 12, marginTop: 4 }}>提示：大小写不敏感；含空格短语请用引号；中文全角！等同 !；若留空将使用传统"匹配模式"兼容。</div>
				</div>
				<div className="form-col" style={{ gridColumn: '1 / -1' }}>
					<div className="label">（兼容）匹配模式列表</div>
					<textarea className="ui-input" style={{ minHeight: 100 }} value={ruleForm.patterns} onChange={(e) => setRuleForm({ ...ruleForm, patterns: e.target.value })} placeholder="多行分隔：每行一个关键字/正则；若填写了 DSL，将优先使用 DSL" />
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
					<div 
						style={{ border: '2px dashed #d1d5db', borderRadius: 8, padding: 24, textAlign: 'center', transition: 'all 0.3s ease' }}
						onDragOver={(e) => {
							e.preventDefault()
							e.currentTarget.style.borderColor = '#3b82f6'
							e.currentTarget.style.backgroundColor = '#eff6ff'
						}}
						onDragLeave={(e) => {
							e.preventDefault()
							e.currentTarget.style.borderColor = '#d1d5db'
							e.currentTarget.style.backgroundColor = 'transparent'
						}}
						onDrop={(e) => {
							e.preventDefault()
							e.currentTarget.style.borderColor = '#d1d5db'
							e.currentTarget.style.backgroundColor = 'transparent'
							const files = Array.from(e.dataTransfer.files)
							if (files.length > 0) {
								handleFileUpload({ target: { files } })
							}
						}}
					>
						<input type="file" multiple onChange={handleFileUpload} style={{ display: 'none' }} id="fileUpload" />
						<label htmlFor="fileUpload" style={{ cursor: 'pointer', color: '#2563eb', fontWeight: 600, display: 'block' }}>
							<div style={{ fontSize: '2rem', marginBottom: 8 }}>📎</div>
							点击选择文件或拖拽到此处
							<div style={{ fontSize: '0.875rem', color: '#6b7280', marginTop: 4 }}>支持多文件同时上传</div>
						</label>
					</div>
				</div>
				<div style={{ 
					background: 'rgba(255,255,255,0.75)', 
					backdropFilter: 'blur(6px)', 
					borderWidth: 1,
					borderStyle: 'solid',
					borderColor: analyzingText ? '#3b82f6' : 'rgba(255,255,255,0.35)',
					borderRadius: 12, 
					padding: 16
				}}>
					<h3 style={{ fontWeight: 600, marginBottom: 8 }}>直接粘贴文本分析（≤ 5MB）</h3>
					<textarea 
						value={pasteText} 
						onChange={(e) => setPasteText(e.target.value)} 
						placeholder="在此粘贴日志文本..." 
						disabled={analyzingText}
						style={{ 
							width: '100%', 
							minHeight: 160, 
							border: '1px solid #e5e7eb', 
							borderRadius: 8, 
							padding: 12, 
							fontFamily: "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace",
							opacity: analyzingText ? 0.6 : 1,
							backgroundColor: analyzingText ? '#f9fafb' : 'white'
						}} 
					/>
					{analyzingText && textAnalysisProgress.message && (
						<div style={{ marginTop: 12, marginBottom: 8 }}>
							<div style={{ fontSize: 12, color: '#3b82f6', marginBottom: 6 }}>{textAnalysisProgress.message}</div>
							<div style={{ 
								width: '100%', 
								height: 4, 
								background: '#e5e7eb', 
								borderRadius: 2, 
								overflow: 'hidden' 
							}}>
								<div style={{ 
									width: `${textAnalysisProgress.progress}%`, 
									height: '100%', 
									background: 'linear-gradient(90deg, #3b82f6, #06b6d4)', 
									borderRadius: 2,
									transition: 'width 0.3s ease'
								}} />
							</div>
							<div style={{ fontSize: 10, color: '#6b7280', marginTop: 2 }}>{Math.round(textAnalysisProgress.progress)}% 完成</div>
						</div>
					)}
					<div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 8 }}>
						<span style={{ color: '#6b7280', fontSize: 12 }}>当前大小：{(new Blob([pasteText]).size / 1024).toFixed(2)} KB</span>
						<button 
							onClick={handleAnalyzeText} 
							disabled={analyzingText || !pasteText}
							style={{ 
								background: analyzingText ? '#9ca3af' : (!pasteText ? '#9ca3af' : '#2563eb'), 
								color: 'white', 
								padding: '8px 14px', 
								borderRadius: 8, 
								border: 'none', 
								cursor: (analyzingText || !pasteText) ? 'not-allowed' : 'pointer',
								display: 'flex',
								alignItems: 'center',
								gap: 6
							}}
						>
							{analyzingText && (
								<div style={{ 
									width: 14, 
									height: 14, 
									border: '2px solid rgba(255,255,255,0.3)', 
									borderTop: '2px solid white', 
									borderRadius: '50%',
									animation: 'spin 1s linear infinite' 
								}} />
							)}
							{analyzingText ? '分析中...' : '分析文本'}
						</button>
					</div>
				</div>
			</div>

			{uploadedFiles.length > 0 && (
				<div style={{ background: 'rgba(255,255,255,0.75)', backdropFilter: 'blur(6px)', border: '1px solid rgba(255,255,255,0.35)', borderRadius: 12, padding: 16, maxHeight: 360, overflow: 'auto' }}>
					<div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
						<h3 style={{ fontWeight: 600, margin: 0 }}>已上传文件 ({uploadedFiles.length})</h3>
						<span style={{ color: '#6b7280', fontSize: 14 }}>💡 双击文件预览内容</span>
					</div>
					{uploadedFiles.map((file: any) => {
						const isAnalyzing = analyzingFiles.has(file.id)
						const progress = analysisProgress[file.id]
						return (
							<div key={file.id} onDoubleClick={() => openFilePreview(file.id, file.filename)} style={{ 
								display: 'flex', 
								justifyContent: 'space-between', 
								alignItems: 'center', 
								padding: 12, 
								borderWidth: 1,
								borderStyle: 'solid',
								borderColor: isAnalyzing ? '#3b82f6' : '#e5e7eb',
								borderRadius: 8, 
								marginBottom: 8, 
								cursor: 'zoom-in',
								background: isAnalyzing ? '#f0f9ff' : 'transparent'
							}}>
								<div style={{ flex: 1 }}>
									<p style={{ fontWeight: 600, margin: 0 }}>{file.filename}</p>
									<p style={{ color: '#6b7280', fontSize: 12, margin: 0 }}>{(file.size / 1024).toFixed(2)} KB - {new Date(file.upload_time).toLocaleString()}</p>
									{isAnalyzing && progress && (
										<div style={{ marginTop: 8 }}>
											<div style={{ fontSize: 11, color: '#3b82f6', marginBottom: 4 }}>{progress.message}</div>
											<div style={{ 
												width: '100%', 
												height: 4, 
												background: '#e5e7eb', 
												borderRadius: 2, 
												overflow: 'hidden' 
											}}>
												<div style={{ 
													width: `${progress.progress}%`, 
													height: '100%', 
													background: 'linear-gradient(90deg, #3b82f6, #06b6d4)', 
													borderRadius: 2,
													transition: 'width 0.3s ease'
												}} />
											</div>
											<div style={{ fontSize: 10, color: '#6b7280', marginTop: 2 }}>{Math.round(progress.progress)}% 完成</div>
										</div>
									)}
								</div>
								<div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
									<button 
										onClick={() => analyzeFile(file.id)} 
										disabled={isAnalyzing}
										style={{ 
											background: isAnalyzing ? '#9ca3af' : '#2563eb', 
											color: 'white', 
											padding: '6px 10px', 
											borderRadius: 6, 
											border: 'none', 
											cursor: isAnalyzing ? 'not-allowed' : 'pointer',
											opacity: isAnalyzing ? 0.6 : 1,
											display: 'flex',
											alignItems: 'center',
											gap: 4
										}}
									>
										{isAnalyzing && (
											<div style={{ 
												width: 12, 
												height: 12, 
												border: '2px solid rgba(255,255,255,0.3)', 
												borderTop: '2px solid white', 
												borderRadius: '50%',
												animation: 'spin 1s linear infinite' 
											}} />
										)}
										{isAnalyzing ? '分析中...' : '分析'}
									</button>
									<button 
										onClick={() => deleteFile(file.id)} 
										disabled={isAnalyzing}
										style={{ 
											background: isAnalyzing ? '#9ca3af' : '#ef4444', 
											color: 'white', 
											padding: '6px 10px', 
											borderRadius: 6, 
											border: 'none', 
											cursor: isAnalyzing ? 'not-allowed' : 'pointer',
											opacity: isAnalyzing ? 0.6 : 1
										}}
									>
										删除
									</button>
								</div>
							</div>
						)
					})}
				</div>
			)}

			<Modal visible={previewVisible} title={previewTitle} onClose={() => setPreviewVisible(false)}>
				<div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8, gap: 8 }}>
					<div style={{ display: 'flex', gap: 8 }}>
						<button onClick={() => setPreviewMode('shell')} style={{ padding: '6px 10px', borderRadius: 6, border: '1px solid #e5e7eb', background: previewMode === 'shell' ? '#111827' : '#fff', color: previewMode === 'shell' ? '#d1fae5' : '#111' }}>Shell</button>
						<button onClick={() => setPreviewMode('txt')} style={{ padding: '6px 10px', borderRadius: 6, border: '1px solid #e5e7eb', background: previewMode === 'txt' ? '#111827' : '#fff', color: previewMode === 'txt' ? '#d1fae5' : '#111' }}>TXT</button>
					</div>
					<div>
						<button onClick={async () => {
							try {
								const st = (window as any).__preview_state__ || {}
								if (!st.fileId) return
								if (st.nextOffset >= st.total) return
								const rr = await authedFetch(`${getApiBase()}/api/logs/${st.fileId}/preview?offset=${st.nextOffset}&size=${512*1024}`)
								if (rr.ok) { const dd = await rr.json(); setPreviewContent(prev => prev + dd.chunk); (window as any).__preview_state__ = { fileId: st.fileId, nextOffset: dd.next_offset, total: dd.total_size } }
							} catch {}
						}} style={{ padding: '6px 10px', borderRadius: 6, border: '1px solid #e5e7eb' }}>加载更多</button>
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
				<div style={{ background: 'rgba(255,255,255,0.75)', backdropFilter: 'blur(6px)', border: '1px solid rgba(255,255,255,0.35)', borderRadius: 12, padding: 12, maxHeight: '70vh', minHeight: '40vh', overflow: 'auto' }}>
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

					<div style={{ background: 'rgba(255,255,255,0.75)', backdropFilter: 'blur(6px)', border: '1px solid rgba(255,255,255,0.35)', borderRadius: 12, padding: 12, maxHeight: '70vh', minHeight: '40vh', overflow: 'auto' }}>
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
				<button key="ok" disabled={!ruleForm.name || !(((ruleForm.dsl||'').trim()) || ((ruleForm.patterns||'').trim()))} onClick={submitRule}>保存</button>
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
					<div style={{ gridColumn: '1 / -1' }}>
						<div style={{ fontSize: 12, color: '#6b7280' }}>规则表达式（DSL）</div>
						<textarea className="ui-input" style={{ minHeight: 120 }} value={ruleForm.dsl} onChange={(e) => setRuleForm({ ...ruleForm, dsl: e.target.value })} placeholder='使用 | & ! () 和引号短语，例如：
OOM | "Out of memory"
("No space left" | "disk full") !write
(("No space left" | "disk full") !write) & "space error"' />
						<div style={{ color: '#6b7280', fontSize: 12, marginTop: 4 }}>提示：大小写不敏感；含空格短语请用引号；中文全角！等同 !；若留空将使用传统"匹配模式"兼容。</div>
					</div>
					<div style={{ gridColumn: '1 / -1' }}>
						<div style={{ fontSize: 12, color: '#6b7280' }}>（兼容）匹配模式列表</div>
						<textarea className="ui-input" style={{ minHeight: 100 }} value={ruleForm.patterns} onChange={(e) => setRuleForm({ ...ruleForm, patterns: e.target.value })} placeholder="多行分隔：每行一个关键字/正则；若填写了 DSL，将优先使用 DSL" />
					</div>
					<div className="form-col">
						<label style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
							<input type="checkbox" checked={!!ruleForm.enabled} onChange={(e) => setRuleForm({ ...ruleForm, enabled: e.target.checked })} /> 启用该规则
						</label>
					</div>
				</div>
			</Modal>
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
				<div style={{ border: '1px solid #e5e7eb', borderRadius: 8, overflow: 'hidden', maxHeight: '60vh', minHeight: '40vh', overflowY: 'auto' }}>
					<div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr', background: '#f9fafb', padding: 12, fontWeight: 600 }}>
						<div>用户名</div><div>邮箱</div><div>角色</div><div>操作</div>
					</div>
					{users.map((user) => (
						<div key={user.id} style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr', padding: 12, borderTop: '1px solid #e5e7eb' }}>
							<div>{user.username}</div><div>{user.email}</div><div>{user.role}</div>
							<div style={{ display: 'flex', gap: 8 }}>
								{user.username !== 'admin' ? (
									<>
										<button onClick={() => openUserEdit(user)} style={{ background: '#10b981', color: 'white', padding: '6px 10px', borderRadius: 6, border: 'none', cursor: 'pointer' }}>编辑</button>
										<button onClick={() => confirmDeleteUser(user.id)} style={{ background: '#ef4444', color: 'white', padding: '6px 10px', borderRadius: 6, border: 'none', cursor: 'pointer' }}>删除</button>
									</>
								) : (
									<span style={{ color: '#9ca3af', fontSize: '12px', padding: '6px 10px' }}>系统管理员</span>
								)}
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
						{userForm.username === 'admin' && userModalMode === 'edit' ? (
							<div style={{ width: '100%', border: '1px solid #e5e7eb', borderRadius: 8, padding: '8px 12px', background: '#f9fafb', color: '#9ca3af', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
								<span>管理员</span>
								<span style={{ fontSize: '10px', background: '#fef3c7', color: '#92400e', padding: '2px 6px', borderRadius: 4 }}>不可修改</span>
							</div>
						) : (
							<select value={userForm.role} onChange={(e) => setUserForm({ ...userForm, role: e.target.value })} style={{ width: '100%', border: '1px solid #e5e7eb', borderRadius: 8, padding: '8px 12px' }}>
								<option value="管理员">管理员</option>
								<option value="普通用户">普通用户</option>
							</select>
						)}
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
				{[{ color: '#059669', value: dashboardStats.uploaded_files, label: '已上传文件' }, { color: '#dc2626', value: dashboardStats.detected_issues, label: '检测到错误' }, { color: '#2563eb', value: dashboardStats.detection_rules, label: '检测规则' }, { color: '#8b5cf6', value: Object.values(problemStatsByType).reduce((a,b)=>a+b,0), label: '问题总数' }, ...(dashboardStats.total_analysis_runs !== undefined ? [{ color: '#f59e0b', value: dashboardStats.total_analysis_runs, label: '全站分析总次数' }] : [])].map((c, i) => (
					<div key={i} style={{ background: 'rgba(255,255,255,0.75)', backdropFilter: 'blur(6px)', border: '1px solid rgba(255,255,255,0.35)', borderRadius: '0.75rem', boxShadow: '0 10px 30px rgba(2,6,23,0.08)', padding: '1.5rem' }}>
						<h3 style={{ color: c.color, fontSize: '2rem', margin: 0 }}>{c.value}</h3>
						<p style={{ color: '#6b7280', margin: 0 }}>{c.label}</p>
					</div>
				))}
			</div>

			<div style={{ background: 'rgba(255,255,255,0.75)', backdropFilter: 'blur(6px)', border: '1px solid rgba(255,255,255,0.35)', borderRadius: '0.75rem', boxShadow: '0 10px 30px rgba(2,6,23,0.08)', padding: '1.5rem', maxHeight: '75vh', minHeight: '50vh', overflow: 'auto' }}>
				<h3 style={{ fontWeight: 600, marginBottom: '1rem' }}>最近分析结果（双击查看详情）</h3>
				{analysisResults.length > 0 ? (
					analysisResults.slice(-20).reverse().map((result, index) => (
						<div key={index} data-analysis-id={result.file_id} onDoubleClick={() => openAnalysisDetail(result.file_id, result.filename)} style={{ padding: '0.75rem', border: '1px solid #e5e7eb', borderRadius: '0.25rem', marginBottom: '0.5rem', cursor: 'zoom-in', background: highlightAnalysisId===result.file_id ? '#e8f7ee' : viewHighlightId===result.file_id ? '#fff7da' : 'transparent', transition: 'background 0.2s ease' }}>
							<p style={{ fontWeight: 600, margin: 0 }}>{result?.filename || '未知文件'}</p>
							{(() => { const sum = (result && result.summary) ? result.summary : { total_issues: 0 }; const ts = result?.analysis_time ? new Date(result.analysis_time).toLocaleString() : ''; return (
								<p style={{ color: '#6b7280', fontSize: '0.875rem', margin: 0 }}>发现 {sum.total_issues || 0} 个问题{ts ? ` - ${ts}` : ''}</p>
							) })()}
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
			if (r.ok) { const d = await r.json(); setProblems(d.problems || []); setProblemPage(1) }
		} catch {}
	}
	const fetchProblemStats = async (types: string[] | null = null) => {
		try {
			const params = types && types.length ? `?types=${encodeURIComponent(types.join(','))}` : ''
			const r = await authedFetch(`${getApiBase()}/api/problems/stats${params}`)
			if (r.ok) { const d = await r.json(); setProblemStatsByType(d.by_type || {}) }
		} catch {}
	}
	const openProblemAdd = async () => {
		// 推断一个合理的默认错误类型
		let defaultType = ''
		try {
			const q = (searchRule || '').toLowerCase()
			const inQuery = (detectionRules || []).find((r:any)=> q && (r.name||'').toLowerCase().includes(q))
			if (inQuery) defaultType = inQuery.name
			if (!defaultType && selectedFolderId) {
				const inFolder = (detectionRules || []).find((r:any)=> r.folder_id === selectedFolderId)
				if (inFolder) defaultType = inFolder.name
			}
			if (!defaultType && (detectionRules||[]).length) defaultType = detectionRules[0].name
		} catch {}
		await ensureAllRulesLoaded()
		setProblemTypeQuery('')
		setProblemForm({ id: null, title: '', url: '', error_type: defaultType, category: '' })
		setProblemModalVisible(true)
	}
	const openProblemEdit = (p: any) => { setProblemForm({ id: p.id, title: p.title, url: p.url, error_type: p.error_type }); setProblemModalVisible(true) }
	const submitProblem = async () => {
		try {
			// 统一清洗：名称去掉链接，链接只保留URL；若名称为空用URL生成
			const cleanedUrl = sanitizeUrl(problemForm.url || '') || sanitizeUrl(problemForm.title || '')
			let cleanedTitle = removeUrls(problemForm.title || '')
			if (!cleanedTitle) cleanedTitle = cleanedUrl ? titleFromUrl(cleanedUrl) : '未命名问题'
			if (!problemForm.error_type) { showToast('请选择问题类型', 'error'); return }
			const payload = { title: cleanedTitle, url: cleanedUrl, error_type: problemForm.error_type }
			if (!payload.url) { showToast('请填写有效链接', 'error'); return }
			let r
			if (problemForm.id) r = await authedFetch(`${getApiBase()}/api/problems/${problemForm.id}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) })
			else r = await authedFetch(`${getApiBase()}/api/problems`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) })
			if (r.ok) { setProblemModalVisible(false); await Promise.all([fetchProblems(problemFilterType, problemFilterQuery, problemFilterCategory), fetchProblemStats(null)]); showToast('问题已保存', 'success') } else showToast('保存失败', 'error')
		} catch { showToast('保存失败', 'error') }
	}
	const deleteProblem = async (id: number) => { const ok = await askConfirm('确定删除该问题？'); if (!ok) return; try { const r = await authedFetch(`${getApiBase()}/api/problems/${id}`, { method: 'DELETE' }); if (r.ok) { await Promise.all([fetchProblems(problemFilterType, problemFilterQuery, problemFilterCategory), fetchProblemStats(null)]); showToast('已删除', 'success') } else showToast('删除失败', 'error') } catch { showToast('删除失败', 'error') } }
	const goToProblems = async (type: string) => {
		clearSelection() // 清除文本选择，防止页面跳转时文本被全选
		setDetailVisible(false)
		setCurrentPage('problems')
		setProblemFilterType(type)
		try {
			const params = new URLSearchParams(); if (type) params.set('error_type', type)
			const [r1, r2] = await Promise.all([
			authedFetch(`${getApiBase()}/api/problems?${params.toString()}`),
			authedFetch(`${getApiBase()}/api/problems/stats?types=${encodeURIComponent(type)}`)
			])
			if (r1.ok) { const d = await r1.json(); const arr = d.problems || []; const firstId = arr[0]?.id || null; setProblems(arr); setHighlightProblemId(firstId); const idx = firstId ? arr.findIndex((x:any)=>x.id===firstId) : 0; setProblemPage(Math.max(1, Math.floor(idx/PROBLEM_PAGE_SIZE)+1)) }
			if (r2.ok) { const d2 = await r2.json(); setProblemStatsByType(d2.by_type || {}) }
		} catch {}
	}

	// 问题库页面
	const ProblemsPage = () => (
		<div style={{ padding: '2rem' }}>
			<h2 style={{ fontSize: '1.5rem', fontWeight: 'bold', marginBottom: '1rem' }}>📚 问题库</h2>
			<div className="ui-card" style={{ padding: 16, marginBottom: 12 }}>
				<div style={{ display: 'grid', gridTemplateColumns: '1fr auto auto', gap: 8, alignItems: 'center' }}>
					<input placeholder="搜索问题（名称/链接/类型/分类）" value={problemFilterQuery} onChange={(e) => setProblemFilterQuery(e.target.value)} style={{ border: '1px solid #e5e7eb', borderRadius: 8, padding: '8px 12px' }} />
					<button className="btn btn-outline" onClick={() => { setHighlightProblemId(null); fetchProblems('', problemFilterQuery, ''); fetchProblemStats(null) }}>查询</button>
					<button className="btn" onClick={() => { setHighlightProblemId(null); setProblemFilterType(''); setProblemFilterQuery(''); setProblemFilterCategory(''); fetchProblems('', '', ''); fetchProblemStats(null) }}>清空</button>
					<button className="btn btn-primary" onClick={openProblemAdd}>+ 新增问题</button>
				</div>
			</div>
			<div className="ui-card" style={{ padding: 16, marginBottom: 12 }}>
				<div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
				<h4 style={{ marginTop: 0 }}>统计</h4>
					<div style={{ color: '#6b7280', fontSize: 12 }}>问题总数：{problems.length}</div>
				</div>
				<div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, maxHeight: statsExpanded ? 260 : 60, overflow: 'auto' }}>
					{Object.entries(problemStatsByType).length === 0 ? (
						<span style={{ color: '#6b7280' }}>暂无统计</span>
					) : (
						Object.entries(problemStatsByType).map(([k,v]) => (
							<button key={k} className="btn" onClick={() => { setProblemFilterType(k); fetchProblems(k, problemFilterQuery, problemFilterCategory); fetchProblemStats(null) }} style={{ background: '#fff' }}>{k}（{v}）</button>
						))
					)}
					<button className="btn btn-outline" onClick={() => { setProblemFilterType(''); fetchProblems('', '', '') }}>全部</button>
					<button className="btn btn-outline" onClick={() => setStatsExpanded(v=>!v)}>{statsExpanded ? '收起' : '展开更多'}</button>
				</div>
			</div>
			<div className="ui-card" style={{ padding: 0, overflow: 'hidden' }}>
				<div style={{ display: 'grid', gridTemplateColumns: '3fr 4fr 2fr 1.5fr', background: '#f9fafb', padding: 12, fontWeight: 600, alignItems: 'center' }}>
					<div style={{ fontSize: '14px' }}>问题名称</div>
					<div style={{ fontSize: '14px' }}>链接</div>
					<div style={{ fontSize: '14px', cursor: 'pointer', userSelect: 'none' }} onClick={() => setProblemSort(s => ({ key: 'error_type', order: s.key==='error_type' && s.order==='asc' ? 'desc' : 'asc' }))}>
						错误类型 {problemSort.key==='error_type' ? (problemSort.order==='asc' ? '↑' : '↓') : ''}
				</div>
					<div style={{ fontSize: '14px' }}>操作</div>
				</div>
				{(() => {
					// 排序后再分页
					let list = [...problems]
					if (problemSort.key === 'error_type') {
						list.sort((a:any,b:any)=>{
							const aa = String(a.error_type||'')
							const bb = String(b.error_type||'')
							return problemSort.order==='asc' ? aa.localeCompare(bb) : bb.localeCompare(aa)
						})
					}
					const pageItems = list.slice((problemPage-1)*PROBLEM_PAGE_SIZE, problemPage*PROBLEM_PAGE_SIZE)
					return (
				<div style={{ maxHeight: 480, overflow: 'auto' }}>
							{pageItems.map((p) => (
								<div id={`problem-row-${p.id}`} key={p.id} style={{ display: 'grid', gridTemplateColumns: '3fr 4fr 2fr 1.5fr', padding: 12, borderTop: '1px solid #e5e7eb', background: (highlightProblemId===p.id?'#eef2ff':'transparent'), alignItems: 'center' }}>
									<div style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', fontSize: '14px', fontWeight: '500', paddingTop: 2 }} title={p.title}>{p.title}</div>
									<div style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', fontSize: '13px', paddingTop: 2 }} title={p.url}><a href={p.url} target="_blank" rel="noreferrer" style={{ color: '#2563eb', textDecoration: 'none' }} onMouseEnter={(e) => (e.target as HTMLElement).style.textDecoration = 'underline'} onMouseLeave={(e) => (e.target as HTMLElement).style.textDecoration = 'none'}>{p.url}</a></div>
									<div style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', fontSize: '12px', color: '#6b7280', paddingTop: 2 }} title={p.error_type}>{p.error_type}</div>
									<div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
								<button onClick={() => openProblemEdit(p)} className="btn">编辑</button>
								<button onClick={() => deleteProblem(p.id)} className="btn btn-danger">删除</button>
							</div>
						</div>
					))}
				</div>
					)
				})()}
				{/* 分页 */}
				{problems.length > PROBLEM_PAGE_SIZE && (
					<div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: 12 }}>
						<button className="btn btn-outline" disabled={problemPage<=1} onClick={()=>setProblemPage(p=>Math.max(1,p-1))}>上一页</button>
						<div style={{ color: '#6b7280' }}>第 {problemPage} / {Math.max(1, Math.ceil(problems.length/PROBLEM_PAGE_SIZE))} 页 · 每页 {PROBLEM_PAGE_SIZE}</div>
						<button className="btn btn-outline" disabled={problemPage>=Math.ceil(problems.length/PROBLEM_PAGE_SIZE)} onClick={()=>setProblemPage(p=>Math.min(Math.ceil(problems.length/PROBLEM_PAGE_SIZE),p+1))}>下一页</button>
					</div>
				)}
			</div>
		</div>
	)

	// —— 工具函数（问题库输入清洗/选择清除） ——
	const sanitizeUrl = (s: string): string => {
		try { const m = String(s || '').match(/https?:\/\/[^\s<>"']+/i); return m ? m[0] : '' } catch { return '' }
	}
	const removeUrls = (s: string): string => {
		try { return String(s || '').replace(/https?:\/\/[^\s<>"']+/ig, '').trim() } catch { return s }
	}
	const titleFromUrl = (u: string): string => {
		try { const url = new URL(u); const segs = url.pathname.split('/').filter(Boolean); const last = segs[segs.length - 1] || url.hostname; return decodeURIComponent(last) } catch { return u }
	}
	const clearSelection = () => { try { const sel = window.getSelection && window.getSelection(); if (sel && sel.removeAllRanges) sel.removeAllRanges() } catch {} }

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

			{/* 个人中心已移至独立页面 /profile */}
			<FolderModal />

			<Toasts toasts={toasts} remove={removeToast} />
			<ConfirmModal visible={confirmState.visible} text={confirmState.text} onConfirm={() => { confirmState.resolve && confirmState.resolve(true); setConfirmState({ visible: false, text: '', resolve: null }) }} onCancel={() => { confirmState.resolve && confirmState.resolve(false); setConfirmState({ visible: false, text: '', resolve: null }) }} />
			{/* 问题新增/编辑 Modal */}
			<Modal visible={problemModalVisible} title={problemForm.id ? '编辑问题' : '新增问题'} onClose={() => setProblemModalVisible(false)} footer={[
				<button key="cancel" className="btn btn-outline" onClick={() => setProblemModalVisible(false)}>取消</button>,
				<button key="ok" className="btn btn-primary" onClick={submitProblem}>保存</button>
			]}>
				<div className="form-grid">
					<div className="form-col"><div className="label">问题名称*</div><input className="ui-input" value={problemForm.title} onChange={(e) => {
						const v = e.target.value
						const detected = sanitizeUrl(v)
						setProblemForm({ ...problemForm, title: removeUrls(v), url: detected || problemForm.url })
					}} onBlur={(e)=> {
						const v = e.target.value
						const detected = sanitizeUrl(v)
						setProblemForm({ ...problemForm, title: removeUrls(v), url: detected || problemForm.url })
					}} /></div>
					<div className="form-col"><div className="label">问题链接*</div><input className="ui-input" value={problemForm.url} onChange={(e) => {
						const v = e.target.value
						setProblemForm({ ...problemForm, url: v })
					}} onBlur={(e)=> {
						const link = sanitizeUrl(e.target.value)
						setProblemForm({ ...problemForm, url: link, title: (problemForm.title ? removeUrls(problemForm.title) : titleFromUrl(link)) })
					}} /></div>
					<div className="form-col" style={{ position: 'relative' }}>
						<div className="label">错误类型*</div>
						<input className="ui-input" placeholder="搜索名称/描述..." value={problemTypeQuery} onChange={(e)=> setProblemTypeQuery(e.target.value)} style={{ marginBottom: 6 }} />
						<select className="ui-select" value={problemForm.error_type} onChange={(e) => setProblemForm({ ...problemForm, error_type: e.target.value })}>
							<option value="">请选择问题类型</option>
							{(allDetectionRules.length ? allDetectionRules : detectionRules)
								.filter((r:any)=>{
									const q = normalizeForSearch(problemTypeQuery)
									if (!q) return true
									const text = normalizeForSearch(`${r.name||''} ${(r.description||'')} ${(r.patterns||[]).join(' ')}`)
									return text.includes(q)
								})
								.map((r:any)=>(<option key={r.id} value={r.name}>{r.name}（{r.description || '无描述'}）</option>))}
						</select>
					</div>
				</div>
			</Modal>
			{/* 全局分析详情 Modal：支持从任何页面打开 */}
			<Modal visible={detailVisible} title={detailData?.title || '分析详情'} onClose={() => setDetailVisible(false)}>
				{detailData && (() => {
					const groups: Record<string, any[]> = {}
					for (const it of detailData.data.issues || []) {
						// 使用规则名称作为分组键，而不是匹配的文本
						const typeKey = String(it.rule_name || '其他')
						const key = typeKey
						groups[key] = groups[key] || []
						groups[key].push(it)
					}
					const entries = Object.entries(groups)
					
					// 获取规则描述的辅助函数
					const getRuleDescription = (ruleName: string) => {
						const rule = allDetectionRules.find((r: any) => r.name === ruleName)
						return rule?.description || ''
					}
					// 解析日志时间（多格式），返回时间戳毫秒
					const monthMap: any = { Jan:0, Feb:1, Mar:2, Apr:3, May:4, Jun:5, Jul:6, Aug:7, Sep:8, Oct:9, Nov:10, Dec:11 }
					const parseTimestampMs = (text: string): { ms: number|null, raw: string } => {
						try {
							const s = String(text || '')
							// ISO 2025-08-27 22:49:12 或 2025-08-27T22:49:12(.sss)?
							let m = s.match(/(\d{4})[-\/.](\d{1,2})[-\/.](\d{1,2})[ T](\d{1,2}):(\d{2})(?::(\d{2}))?/)
							if (m) {
								const [_, y, mo, d, h, mi, se] = m
								const date = new Date(Number(y), Number(mo)-1, Number(d), Number(h), Number(mi), se?Number(se):0)
								return { ms: date.getTime(), raw: m[0] }
							}
							// Syslog: Aug 27 22:49:12
							m = s.match(/\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(\d{1,2})\s+(\d{2}):(\d{2}):(\d{2})\b/)
							if (m) {
								const now = new Date()
								const [_, mon, d, h, mi, se] = m
								const date = new Date(now.getFullYear(), monthMap[mon], Number(d), Number(h), Number(mi), Number(se))
								return { ms: date.getTime(), raw: m[0] }
							}
							// 尝试 Date.parse
							m = s.match(/\d{4}[^\n]{0,20}(\d{2}:?\d{2}:?\d{2})/)
							if (m) {
								const t = Date.parse(m[0])
								if (!Number.isNaN(t)) return { ms: t, raw: m[0] }
							}
							return { ms: null, raw: '' }
						} catch { return { ms: null, raw: '' } }
					}
					// 找出最接近当前时间的一个错误
					let nearest: { issue: any|null, diff: number, when: string } = { issue: null, diff: Number.POSITIVE_INFINITY, when: '' }
					const nowMs = Date.now()
					for (const it of (detailData.data.issues || [])) {
						const src = `${it.context || ''} ${it.matched_text || ''}`
						const { ms, raw } = parseTimestampMs(src)
						if (ms !== null) {
							const diff = Math.abs(nowMs - ms)
							if (diff < nearest.diff) nearest = { issue: it, diff, when: raw }
						}
					}
					return (
						<div style={{ maxHeight: '65vh', overflow: 'auto', fontFamily: 'ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Noto Sans, Ubuntu, Cantarell, Helvetica Neue, Arial' }}>
							<div style={{ color: '#6b7280', fontSize: 12, marginBottom: 8 }}>共 {detailData.data.summary.total_issues} 个问题，{entries.length} 个类型</div>
							{/* 最新错误置顶块 */}
							{nearest.issue && (
								<div style={{ border: '1px solid #fde68a', background: '#fffbeb', padding: 10, borderRadius: 10, marginBottom: 10 }}>
									<div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
										<span style={{ fontSize: 12, background: '#f59e0b', color: '#fff', padding: '2px 6px', borderRadius: 6 }}>最新错误</span>
										<span style={{ fontWeight: 800, color: '#dc2626' }}>{String(nearest.issue.rule_name || '问题')}</span>
										{nearest.when && <span style={{ color: '#6b7280', fontSize: 12 }}>时间 {nearest.when}</span>}
									</div>
									<pre style={{ margin: 0, whiteSpace: 'pre-wrap', color: '#374151', fontSize: '13px', lineHeight: 1.4 }}>{nearest.issue.context || nearest.issue.matched_text || ''}</pre>
								</div>
							)}
							{entries.map(([typeKey, list], gi) => {
								const page = pageByGroup[typeKey] || 1
								const shown = (list as any[]).slice(0, page * PAGE_SIZE_PER_GROUP)
								const ruleDescription = getRuleDescription(typeKey)
								return (
									<div key={gi} style={{ border: '1px solid #e5e7eb', borderRadius: 10, padding: 10, marginBottom: 10 }}>
										<div onClick={() => setCollapsedGroups(v => ({ ...v, [typeKey]: !v[typeKey] }))} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', cursor: 'pointer', userSelect: 'none' }}>
											<div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
												<div style={{ fontWeight: 800, color: '#dc2626' }}>{typeKey}</div>
												{ruleDescription && <div style={{ color: '#dc2626', fontSize: 14, fontWeight: 800 }}>- {ruleDescription}</div>}
												<span style={{ color: '#6b7280', fontSize: 12 }}>({Array.isArray(list)?list.length:0} 条)</span>
											</div>
											<div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
												<span style={{ color: '#6b7280', fontSize: 12 }}>问题库：{problemStatsByType[typeKey] || 0}</span>
												<button onClick={(e) => { e.stopPropagation(); clearSelection(); goToProblems(typeKey) }} style={{ border: '1px solid #e5e7eb', background: '#fff', padding: '4px 8px', borderRadius: 6, cursor: 'pointer' }}>查看</button>
											</div>
										</div>
										{!collapsedGroups[typeKey] && (
											<div>
												{shown.map((it: any, ii: number) => {
													const isNearest = nearest.issue && it === nearest.issue
													return (
													<div key={ii} style={{ padding: '6px 8px', borderTop: '1px dashed #e5e7eb', fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace' }}>
														<div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
															<div style={{ color: '#6b7280', fontSize: 12 }}>
																行 {it.line_number ? (typeof it.line_number === 'string' ? parseInt(it.line_number) || '-' : it.line_number) : '-'}
															</div>
																{isNearest && (<span style={{ fontSize: 10, background: '#f59e0b', color: '#fff', padding: '2px 6px', borderRadius: 6 }}>最新错误</span>)}
														</div>
														<pre style={{ margin: '0', whiteSpace: 'pre-wrap', color: '#374151', fontSize: '13px', lineHeight: '1.4' }}>{it.context || it.matched_text || ''}</pre>
													</div>
														)
												})}
												{shown.length < (list as any[]).length && (
													<div style={{ textAlign: '中心', padding: 8 }}>
														<button onClick={() => setPageByGroup(v => ({ ...v, [typeKey]: (v[typeKey] || 1) + 1 }))} style={{ border: '1px solid #e5e7eb', background: '#fff', padding: '6px 12px', borderRadius: 8, cursor: 'pointer' }}>
															加载更多（{(list as any[]).length - shown.length}）
														</button>
													</div>
												)}
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
 