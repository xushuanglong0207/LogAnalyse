// @ts-nocheck
'use client'

import { useState, useEffect, useRef, useMemo } from 'react'
import { useRouter } from 'next/navigation'
import { 
	FileText, 
	Upload, 
	Trash2, 
	Play, 
	Eye,
	Search,
	ArrowLeft,
	FolderOpen,
	AlertCircle,
	CheckCircle
} from 'lucide-react'

function computeApiBase(): string {
	if (typeof window !== 'undefined') {
		const protocol = window.location.protocol
		const host = window.location.hostname
		return `${protocol}//${host}:8001`
	}
	return ''
}

export default function LogsPage() {
	const router = useRouter()
	const [apiBase] = useState(computeApiBase())
	const [loading, setLoading] = useState(true)
	const [uploadedFiles, setUploadedFiles] = useState<any[]>([])
	const [pasteText, setPasteText] = useState('')
	const [uploading, setUploading] = useState(false)
	const [analyzing, setAnalyzing] = useState<number | null>(null)
	
	// 预览相关状态
	const [previewVisible, setPreviewVisible] = useState(false)
	const [previewTitle, setPreviewTitle] = useState('')
	const [previewContent, setPreviewContent] = useState('')
	const [previewMode, setPreviewMode] = useState<'shell' | 'txt'>('shell')

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
		// 简单的toast实现
		console.log(`${type}: ${message}`)
	}

	const fetchUploadedFiles = async () => {
		try { 
			const r = await authedFetch(`${apiBase}/api/logs`)
			if (r.ok) { 
				const d = await r.json()
				setUploadedFiles(d.files || []) 
			} 
		} catch (err) {
			console.error('获取文件列表失败')
		}
	}

	const handleFileUpload = async (e: any) => {
		try {
			setUploading(true)
			const files = Array.from(e.target.files || [])
			for (const f of files as any[]) {
				const fd = new FormData()
				fd.append('file', f)
				const r = await authedFetch(`${apiBase}/api/logs/upload`, { method: 'POST', body: fd })
				if (!r.ok) throw new Error('上传失败')
			}
			await fetchUploadedFiles()
			showToast('文件上传成功', 'success')
		} catch (err) {
			showToast('文件上传失败', 'error')
		} finally {
			setUploading(false)
			try { e.target.value = '' } catch {}
		}
	}

	const handleAnalyzeText = async () => {
		try {
			if (!pasteText) return showToast('请先粘贴内容', 'info')
			setUploading(true)
			const r = await authedFetch(`${apiBase}/api/logs/analyze_text`, { 
				method: 'POST', 
				headers: { 'Content-Type': 'application/json' }, 
				body: JSON.stringify({ text: pasteText, filename: 'pasted.log' }) 
			})
			if (r.ok) {
				await fetchUploadedFiles()
				setPasteText('')
				showToast('分析完成', 'success')
			} else {
				showToast('分析失败', 'error')
			}
		} catch (err) { 
			showToast('分析失败', 'error') 
		} finally {
			setUploading(false)
		}
	}

	const analyzeFile = async (fileId: number) => {
		try { 
			setAnalyzing(fileId)
			const r = await authedFetch(`${apiBase}/api/logs/${fileId}/analyze`, { method: 'POST' })
			if (r.ok) { 
				showToast('分析完成', 'success')
			} else {
				showToast('分析失败', 'error')
			}
		} catch (err) { 
			showToast('分析失败', 'error') 
		} finally {
			setAnalyzing(null)
		}
	}

	const deleteFile = async (fileId: number) => {
		if (!confirm('确定删除该日志文件？')) return
		
		try { 
			const r = await authedFetch(`${apiBase}/api/logs/${fileId}`, { method: 'DELETE' })
			if (r.ok) { 
				await fetchUploadedFiles()
				showToast('删除成功', 'success') 
			} else {
				showToast('删除失败', 'error')
			}
		} catch (err) { 
			showToast('删除失败', 'error') 
		}
	}

	const openFilePreview = async (fileId: number, filename: string) => {
		try { 
			const r = await authedFetch(`${apiBase}/api/logs/${fileId}`)
			if (r.ok) { 
				const d = await r.json()
				setPreviewTitle(filename)
				setPreviewContent(d.content || '')
				setPreviewMode('shell')
				setPreviewVisible(true)
			} 
		} catch (err) {
			showToast('预览失败', 'error')
		}
	}

	useEffect(() => {
		if (!getStoredToken()) {
			router.replace('/login')
			return
		}

		const initData = async () => {
			await fetchUploadedFiles()
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
								<div className="w-10 h-10 bg-gradient-to-br from-orange-500 to-red-600 rounded-xl flex items-center justify-center">
									<FileText className="w-6 h-6 text-white" />
								</div>
								<h1 className="text-2xl font-bold text-gray-900">日志管理</h1>
							</div>
						</div>
						<div className="flex items-center space-x-2 text-sm text-gray-600">
							<FolderOpen className="w-4 h-4" />
							<span>{uploadedFiles.length} 个文件</span>
						</div>
					</div>
				</div>
			</header>

			<div className="max-w-7xl mx-auto px-4 py-8 space-y-8">
				{/* Upload Section */}
				<div className="grid md:grid-cols-2 gap-6">
					{/* File Upload */}
					<div className="bg-white/70 backdrop-blur-xl rounded-2xl shadow-xl border border-white/50 p-6">
						<h3 className="text-lg font-bold text-gray-900 mb-4 flex items-center">
							<Upload className="w-5 h-5 mr-2 text-blue-600" />
							文件上传
						</h3>
						<div className="border-2 border-dashed border-gray-300 hover:border-blue-400 rounded-xl p-8 text-center transition-colors duration-200">
							<input 
								type="file" 
								multiple 
								onChange={handleFileUpload} 
								className="hidden" 
								id="fileUpload"
								disabled={uploading}
							/>
							<label htmlFor="fileUpload" className="cursor-pointer">
								{uploading ? (
									<div className="flex flex-col items-center">
										<div className="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mb-3"></div>
										<p className="text-blue-600 font-medium">上传中...</p>
									</div>
								) : (
									<div className="flex flex-col items-center">
										<div className="w-12 h-12 bg-blue-100 rounded-full flex items-center justify-center mb-3">
											<Upload className="w-6 h-6 text-blue-600" />
										</div>
										<p className="text-blue-600 font-medium">点击选择文件</p>
										<p className="text-gray-500 text-sm mt-1">支持任意格式的日志文件</p>
									</div>
								)}
							</label>
						</div>
					</div>

					{/* Text Analysis */}
					<div className="bg-white/70 backdrop-blur-xl rounded-2xl shadow-xl border border-white/50 p-6">
						<h3 className="text-lg font-bold text-gray-900 mb-4 flex items-center">
							<FileText className="w-5 h-5 mr-2 text-green-600" />
							文本分析
						</h3>
						<textarea
							value={pasteText}
							onChange={(e) => setPasteText(e.target.value)}
							placeholder="在此粘贴日志文本进行即时分析..."
							className="w-full h-32 border border-gray-200 rounded-xl px-4 py-3 resize-none focus:ring-4 focus:ring-blue-500/10 focus:border-blue-500 transition-all duration-200"
						/>
						<div className="flex justify-between items-center mt-4">
							<span className="text-sm text-gray-500">
								大小: {(new Blob([pasteText]).size / 1024).toFixed(2)} KB
							</span>
							<button
								onClick={handleAnalyzeText}
								disabled={!pasteText || uploading}
								className="px-4 py-2 bg-gradient-to-r from-green-500 to-emerald-600 hover:from-green-600 hover:to-emerald-700 disabled:from-gray-400 disabled:to-gray-500 text-white font-medium rounded-lg shadow-lg hover:shadow-xl disabled:shadow-none transition-all duration-200 disabled:cursor-not-allowed flex items-center space-x-2"
							>
								{uploading ? (
									<>
										<div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
										<span>分析中...</span>
									</>
								) : (
									<>
										<Play className="w-4 h-4" />
										<span>开始分析</span>
									</>
								)}
							</button>
						</div>
					</div>
				</div>

				{/* Files List */}
				<div className="bg-white/70 backdrop-blur-xl rounded-2xl shadow-xl border border-white/50 overflow-hidden">
					<div className="p-6 border-b border-gray-100">
						<h3 className="text-lg font-bold text-gray-900 flex items-center">
							<FolderOpen className="w-5 h-5 mr-2 text-blue-600" />
							已上传文件 ({uploadedFiles.length})
						</h3>
					</div>

					{uploadedFiles.length > 0 ? (
						<div className="max-h-96 overflow-auto">
							<div className="divide-y divide-gray-100">
								{uploadedFiles.map((file: any) => (
									<div key={file.id} className="p-4 hover:bg-gray-50/50 transition-colors duration-200 group">
										<div className="flex items-center justify-between">
											<div 
												className="flex-1 cursor-pointer"
												onDoubleClick={() => openFilePreview(file.id, file.filename)}
											>
												<div className="flex items-center space-x-3">
													<div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
														<FileText className="w-5 h-5 text-blue-600" />
													</div>
													<div>
														<h4 className="font-medium text-gray-900 group-hover:text-blue-600 transition-colors duration-200">
															{file.filename}
														</h4>
														<p className="text-sm text-gray-500">
															{(file.size / 1024).toFixed(2)} KB • {new Date(file.upload_time).toLocaleString()}
														</p>
													</div>
												</div>
											</div>
											<div className="flex items-center space-x-2">
												<button
													onClick={() => analyzeFile(file.id)}
													disabled={analyzing === file.id}
													className="px-3 py-1.5 bg-blue-100 hover:bg-blue-200 text-blue-600 rounded-lg text-sm font-medium transition-colors duration-200 disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-1"
												>
													{analyzing === file.id ? (
														<>
															<div className="w-3 h-3 border-2 border-blue-600/30 border-t-blue-600 rounded-full animate-spin"></div>
															<span>分析中</span>
														</>
													) : (
														<>
															<Play className="w-3 h-3" />
															<span>分析</span>
														</>
													)}
												</button>
												<button
													onClick={() => openFilePreview(file.id, file.filename)}
													className="px-3 py-1.5 bg-green-100 hover:bg-green-200 text-green-600 rounded-lg text-sm font-medium transition-colors duration-200 flex items-center space-x-1"
												>
													<Eye className="w-3 h-3" />
													<span>预览</span>
												</button>
												<button
													onClick={() => deleteFile(file.id)}
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
						</div>
					) : (
						<div className="p-12 text-center">
							<div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
								<FolderOpen className="w-8 h-8 text-gray-400" />
							</div>
							<p className="text-gray-500 font-medium mb-2">暂无上传文件</p>
							<p className="text-gray-400 text-sm">上传日志文件开始分析</p>
						</div>
					)}
				</div>
			</div>

			{/* Preview Modal */}
			{previewVisible && (
				<div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
					<div className="bg-white rounded-2xl shadow-2xl max-w-6xl w-full max-h-[80vh] flex flex-col">
						<div className="p-6 border-b border-gray-100 flex items-center justify-between">
							<h3 className="text-lg font-bold text-gray-900">{previewTitle}</h3>
							<div className="flex items-center space-x-2">
								<button
									onClick={() => setPreviewMode('shell')}
									className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors duration-200 ${
										previewMode === 'shell' ? 'bg-gray-900 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
									}`}
								>
									Shell
								</button>
								<button
									onClick={() => setPreviewMode('txt')}
									className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors duration-200 ${
										previewMode === 'txt' ? 'bg-gray-900 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
									}`}
								>
									Text
								</button>
								<button
									onClick={() => setPreviewVisible(false)}
									className="ml-2 w-8 h-8 bg-gray-100 hover:bg-gray-200 rounded-lg flex items-center justify-center text-gray-600 transition-colors duration-200"
								>
									×
								</button>
							</div>
						</div>
						<div className="flex-1 overflow-auto">
							{previewMode === 'shell' ? (
								<div className="bg-gray-900 text-green-400 p-4 font-mono text-sm leading-relaxed">
									<pre className="whitespace-pre-wrap">{previewContent}</pre>
								</div>
							) : (
								<div className="bg-white text-gray-900 p-4 font-mono text-sm leading-relaxed">
									<pre className="whitespace-pre-wrap">{previewContent}</pre>
								</div>
							)}
						</div>
					</div>
				</div>
			)}
		</div>
	)
}