'use client'
import { useEffect } from 'react'
import { usePathname, useRouter } from 'next/navigation'

export default function RootLayout({ children }: { children: React.ReactNode }) {
	const pathname = usePathname()
	const router = useRouter()
	useEffect(() => {
		if (typeof window === 'undefined') return
		const token = localStorage.getItem('token') || sessionStorage.getItem('token')
		if (!token && pathname !== '/login') {
			router.replace('/login')
		}
		if (token && pathname === '/login') {
			router.replace('/')
		}
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