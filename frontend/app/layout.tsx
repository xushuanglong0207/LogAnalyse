'use client'
import { useEffect, useRef } from 'react'
import { usePathname, useRouter } from 'next/navigation'

export default function RootLayout({ children }: { children: React.ReactNode }) {
	const pathname = usePathname()
	const router = useRouter()
	const isRedirecting = useRef(false)
	useEffect(() => {
		if (typeof window === 'undefined') return
		if (isRedirecting.current) return
		const token = localStorage.getItem('token') || sessionStorage.getItem('token')
		if (!token && pathname !== '/login') {
			isRedirecting.current = true
			router.replace('/login')
		} else if (token && pathname === '/login') {
			isRedirecting.current = true
			router.replace('/')
		}
		const t = setTimeout(() => { isRedirecting.current = false }, 600)
		return () => clearTimeout(t)
	}, [pathname, router])
	return (
		<html lang="zh-CN">
			<head>
				<title>日志分析平台</title>
				<link rel="icon" href="/icon.svg" />
			</head>
			<body style={{ margin: 0 }}>{children}</body>
		</html>
	)
} 